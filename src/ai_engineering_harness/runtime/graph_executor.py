"""Canonical traversal of compiled graphs over durable execution state."""

from __future__ import annotations

import hashlib
import math
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Literal

from jsonschema import SchemaError as JsonSchemaError
from jsonschema import ValidationError as JsonValidationError
from jsonschema import validate as validate_json_schema
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    CompiledGraphArtifact,
    NodeSpec,
    ResolvedContractSpec,
    TerminalStateSpec,
)
from ai_engineering_harness.contracts.events import ExecutionEvent
from ai_engineering_harness.contracts.execution import ExecutionId, ExecutionRecord
from ai_engineering_harness.persistence import ExecutionLock, StateStorageProvider

from .node_executors import (
    NodeBackendError,
    NodeExecutionContext,
    NodeExecutionFailure,
    NodeExecutionResult,
    NodeExecutor,
    NodeExecutorError,
    NodeExecutorRegistry,
    NodeExecutorResultError,
    _copy_json_object,
)


class GraphExecutionError(Exception):
    """Base class for fail-closed graph traversal errors."""

    def __init__(
        self,
        message: str,
        *,
        execution_id: str | None = None,
        node_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.execution_id = execution_id
        self.node_id = node_id


class ArtifactExecutionMismatchError(GraphExecutionError):
    """The artifact is invalid or does not match immutable execution identity."""


class UnknownCurrentNodeError(GraphExecutionError):
    """The persisted current node is absent from the compiled graph."""


class NodeContractNotFoundError(GraphExecutionError):
    """An agent contract reference is absent or ambiguous in the artifact."""


class NodeInputValidationError(GraphExecutionError):
    """A node input is not a JSON object or violates its declared contract."""


class NodeOutputValidationError(GraphExecutionError):
    """A successful node output violates its declared contract."""


class GraphCycleExecutionError(GraphExecutionError):
    """Traversal attempted a retry/cycle reserved for F2.6."""


class GraphClockError(GraphExecutionError):
    """The injected clock is invalid or regresses durable execution time."""


class GraphEventConstructionError(GraphExecutionError):
    """A canonical node event could not be constructed."""


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class GraphExecutionResult(_StrictFrozenModel):
    """Final terminal reached by one locked graph traversal call."""

    execution_id: ExecutionId
    terminal_id: str = Field(min_length=1)
    outcome: Literal["success", "failure"]
    output: dict[str, object]
    executed_node_ids: tuple[str, ...]
    final_revision: int = Field(ge=0)
    fencing_token: int = Field(gt=0)
    failure: NodeExecutionFailure | None = None

    @field_validator("output", mode="before")
    @classmethod
    def detach_output(cls, value: object) -> dict[str, object]:
        return _copy_json_object(value, path="output")

    @field_validator("executed_node_ids", mode="before")
    @classmethod
    def freeze_node_ids(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def require_matching_failure(self) -> GraphExecutionResult:
        if self.outcome == "success" and self.failure is not None:
            raise ValueError("a successful graph result cannot contain failure details")
        if self.outcome == "failure" and self.failure is None:
            raise ValueError("a failed graph result requires failure details")
        return self


class GraphExecutor:
    """Execute only nodes and edges declared by a canonical compiled artifact."""

    def __init__(
        self,
        storage: StateStorageProvider,
        executors: NodeExecutorRegistry,
        *,
        lock_timeout_seconds: float = 30.0,
        clock: Callable[[], datetime] | None = None,
        event_id_factory: Callable[[], str] | None = None,
        owner_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(storage, StateStorageProvider):
            raise TypeError("storage must implement StateStorageProvider")
        if not isinstance(executors, NodeExecutorRegistry):
            raise TypeError("executors must be a NodeExecutorRegistry")
        if (
            isinstance(lock_timeout_seconds, bool)
            or not isinstance(lock_timeout_seconds, (int, float))
            or not math.isfinite(lock_timeout_seconds)
            or lock_timeout_seconds < 0
        ):
            raise ValueError("lock_timeout_seconds must be finite and non-negative")
        self._storage = storage
        self._executors = executors
        self._lock_timeout_seconds = float(lock_timeout_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._event_id_factory = event_id_factory or (
            lambda: f"event-{uuid.uuid4().hex}"
        )
        self._owner_id_factory = owner_id_factory or (
            lambda: f"graph-executor-{uuid.uuid4().hex}"
        )

    def execute(
        self,
        artifact: CompiledGraphArtifact,
        execution_id: str,
        initial_input: dict[str, object],
    ) -> GraphExecutionResult:
        """Traverse from the persisted current node under one execution lock."""
        detached_artifact = self._detach_artifact(artifact, execution_id=execution_id)
        try:
            current_payload = _copy_json_object(initial_input, path="initial_input")
        except (TypeError, ValueError) as exc:
            raise NodeInputValidationError(
                "initial input must be a finite JSON object",
                execution_id=execution_id,
            ) from exc

        lock = self._storage.acquire_execution_lock(
            execution_id,
            self._owner_id_factory(),
            timeout_seconds=self._lock_timeout_seconds,
        )
        try:
            return self._execute_locked(
                detached_artifact,
                execution_id,
                current_payload,
                lock,
            )
        finally:
            self._storage.release_execution_lock(lock)

    def _execute_locked(
        self,
        artifact: CompiledGraphArtifact,
        execution_id: str,
        initial_input: dict[str, object],
        lock: ExecutionLock,
    ) -> GraphExecutionResult:
        nodes = {node.id: node for node in artifact.graph.nodes}
        terminals = {terminal.id: terminal for terminal in artifact.graph.terminal_states}
        record = self._storage.load_execution(execution_id, lock=lock)
        self._validate_execution_identity(record, artifact)

        current_payload = initial_input
        visited: set[str] = set()
        executed_node_ids: list[str] = []
        last_failure: NodeExecutionFailure | None = None

        while True:
            current_id = record.current_node_id
            terminal = terminals.get(current_id)
            if terminal is not None:
                return self._resolve_terminal(
                    artifact,
                    record,
                    terminal,
                    current_payload,
                    tuple(executed_node_ids),
                    last_failure,
                    lock,
                )

            node = nodes.get(current_id)
            if node is None:
                raise UnknownCurrentNodeError(
                    f"current node {current_id!r} is not declared by the artifact",
                    execution_id=execution_id,
                    node_id=current_id,
                )
            if current_id in visited:
                raise GraphCycleExecutionError(
                    "node revisit requires F2.6 retry semantics",
                    execution_id=execution_id,
                    node_id=current_id,
                )

            self._validate_node_input(artifact, node, current_payload, execution_id)
            executor = self._executors.select(node)
            executor.ensure_available()
            attempt = record.attempt_by_node.get(current_id, 0) + 1
            started_at = self._next_timestamp(
                record.updated_at,
                execution_id=execution_id,
                node_id=current_id,
            )
            context = NodeExecutionContext(
                execution_id=execution_id,
                artifact=artifact,
                node=node,
                attempt=attempt,
                input_payload=current_payload,
                fencing_token=lock.fencing_token,
            )
            self._append_node_event(
                execution_id,
                node,
                "NODE_STARTED",
                attempt,
                lock,
                started_at,
            )

            result = self._execute_node(executor, context)
            if result.succeeded:
                try:
                    self._validate_node_output(
                        artifact,
                        node,
                        result.output,
                        execution_id,
                    )
                except NodeOutputValidationError:
                    result = NodeExecutionResult.failed(
                        {},
                        code="invalid_node_output",
                        message="node output did not satisfy its declared contract",
                        retryable=False,
                    )

            next_id = node.on_success if result.succeeded else node.on_failure
            outcome_type: Literal["NODE_COMPLETED", "NODE_FAILED"] = (
                "NODE_COMPLETED" if result.succeeded else "NODE_FAILED"
            )
            outcome_at = self._next_timestamp(
                started_at,
                execution_id=execution_id,
                node_id=current_id,
            )
            self._append_node_event(
                execution_id,
                node,
                outcome_type,
                attempt,
                lock,
                outcome_at,
                next_id=next_id,
                failure=result.failure,
            )

            replacement = self._next_record(
                record,
                next_id=next_id,
                node_id=current_id,
                attempt=attempt,
                updated_at=outcome_at,
            )
            record = self._storage.compare_and_set_execution(
                execution_id,
                record.revision,
                replacement,
                lock=lock,
            )
            visited.add(current_id)
            executed_node_ids.append(current_id)
            current_payload = result.output
            last_failure = result.failure

    def _resolve_terminal(
        self,
        artifact: CompiledGraphArtifact,
        record: ExecutionRecord,
        terminal: TerminalStateSpec,
        payload: dict[str, object],
        executed_node_ids: tuple[str, ...],
        last_failure: NodeExecutionFailure | None,
        lock: ExecutionLock,
    ) -> GraphExecutionResult:
        executor = self._executors.select(terminal)
        executor.ensure_available()
        terminal_result = executor.execute(
            NodeExecutionContext(
                execution_id=record.execution_id,
                artifact=artifact,
                node=terminal,
                attempt=0,
                input_payload=payload,
                fencing_token=lock.fencing_token,
            )
        )
        failure = None
        if terminal.outcome == "failure":
            failure = last_failure or terminal_result.failure
        return GraphExecutionResult(
            execution_id=record.execution_id,
            terminal_id=terminal.id,
            outcome=terminal.outcome,
            output=terminal_result.output,
            executed_node_ids=executed_node_ids,
            final_revision=record.revision,
            fencing_token=lock.fencing_token,
            failure=failure,
        )

    @staticmethod
    def _execute_node(
        executor: NodeExecutor,
        context: NodeExecutionContext,
    ) -> NodeExecutionResult:
        try:
            result = executor.execute(context)
        except NodeBackendError as exc:
            return NodeExecutionResult.failed(
                {},
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
            )
        except NodeExecutorResultError as exc:
            return NodeExecutionResult.failed(
                {},
                code="invalid_node_result",
                message=str(exc),
                retryable=False,
            )
        except NodeExecutorError:
            raise
        if not isinstance(result, NodeExecutionResult):
            return NodeExecutionResult.failed(
                {},
                code="invalid_node_result",
                message="node executor returned an invalid result",
                retryable=False,
            )
        return result

    def _append_node_event(
        self,
        execution_id: str,
        node: NodeSpec,
        event_type: Literal["NODE_STARTED", "NODE_COMPLETED", "NODE_FAILED"],
        attempt: int,
        lock: ExecutionLock,
        timestamp: datetime,
        *,
        next_id: str | None = None,
        failure: NodeExecutionFailure | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "attempt": attempt,
            "fencing_token": lock.fencing_token,
            "node_id": node.id,
            "node_type": node.type,
        }
        if next_id is not None:
            payload["next_id"] = next_id
        if failure is not None:
            payload["error_code"] = failure.code
            payload["retryable"] = failure.retryable
        try:
            event = ExecutionEvent(
                event_id=self._event_id_factory(),
                execution_id=execution_id,
                event_type=event_type,
                timestamp=timestamp,
                payload=payload,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise GraphEventConstructionError(
                "cannot construct a canonical node event",
                execution_id=execution_id,
                node_id=node.id,
            ) from exc
        self._storage.append_event(execution_id, event, lock=lock)

    @staticmethod
    def _next_record(
        record: ExecutionRecord,
        *,
        next_id: str,
        node_id: str,
        attempt: int,
        updated_at: datetime,
    ) -> ExecutionRecord:
        attempts = dict(record.attempt_by_node)
        attempts[node_id] = attempt
        document = record.model_dump(mode="python")
        document.update(
            {
                "revision": record.revision + 1,
                "current_node_id": next_id,
                "attempt_by_node": attempts,
                "updated_at": updated_at,
            }
        )
        return ExecutionRecord.model_validate(document)

    @staticmethod
    def _validate_execution_identity(
        record: ExecutionRecord,
        artifact: CompiledGraphArtifact,
    ) -> None:
        artifact_digest = "sha256:" + hashlib.sha256(
            artifact.canonical_json().encode("utf-8")
        ).hexdigest()
        if (
            record.workflow_name != artifact.graph.graph.name
            or record.artifact_digest != artifact_digest
        ):
            raise ArtifactExecutionMismatchError(
                "execution record does not match the compiled artifact identity",
                execution_id=record.execution_id,
                node_id=record.current_node_id,
            )

    @staticmethod
    def _detach_artifact(
        artifact: CompiledGraphArtifact,
        *,
        execution_id: str,
    ) -> CompiledGraphArtifact:
        if not isinstance(artifact, CompiledGraphArtifact):
            raise ArtifactExecutionMismatchError(
                "artifact must be a CompiledGraphArtifact",
                execution_id=execution_id,
            )
        try:
            return CompiledGraphArtifact.model_validate_json(artifact.canonical_json())
        except (TypeError, ValueError, ValidationError) as exc:
            raise ArtifactExecutionMismatchError(
                "compiled artifact failed integrity validation",
                execution_id=execution_id,
            ) from exc

    def _next_timestamp(
        self,
        minimum: datetime,
        *,
        execution_id: str,
        node_id: str,
    ) -> datetime:
        observed = self._clock()
        if (
            not isinstance(observed, datetime)
            or observed.tzinfo is None
            or observed.utcoffset() is None
            or observed.utcoffset() != timedelta(0)
            or observed < minimum
        ):
            raise GraphClockError(
                "graph clock must be UTC and cannot regress durable time",
                execution_id=execution_id,
                node_id=node_id,
            )
        return observed.astimezone(UTC)

    def _validate_node_input(
        self,
        artifact: CompiledGraphArtifact,
        node: NodeSpec,
        payload: dict[str, object],
        execution_id: str,
    ) -> None:
        if not isinstance(node, AgentNodeSpec):
            return
        contract = self._contract_for(artifact, node.input_contract, execution_id, node.id)
        self._validate_schema(
            contract,
            payload,
            error_type=NodeInputValidationError,
            execution_id=execution_id,
            node_id=node.id,
        )

    def _validate_node_output(
        self,
        artifact: CompiledGraphArtifact,
        node: NodeSpec,
        payload: dict[str, object],
        execution_id: str,
    ) -> None:
        if not isinstance(node, AgentNodeSpec):
            return
        contract = self._contract_for(artifact, node.output_contract, execution_id, node.id)
        self._validate_schema(
            contract,
            payload,
            error_type=NodeOutputValidationError,
            execution_id=execution_id,
            node_id=node.id,
        )

    @staticmethod
    def _contract_for(
        artifact: CompiledGraphArtifact,
        reference: str,
        execution_id: str,
        node_id: str,
    ) -> ResolvedContractSpec:
        matches = tuple(
            contract
            for contract in artifact.resolved_contracts
            if contract.requested_reference == reference
        )
        if len(matches) != 1:
            raise NodeContractNotFoundError(
                f"contract reference {reference!r} is absent or ambiguous",
                execution_id=execution_id,
                node_id=node_id,
            )
        return matches[0]

    @staticmethod
    def _validate_schema(
        contract: ResolvedContractSpec,
        payload: Mapping[str, object],
        *,
        error_type: type[GraphExecutionError],
        execution_id: str,
        node_id: str,
    ) -> None:
        try:
            contract.verify_integrity()
            validate_json_schema(instance=payload, schema=contract.contract_schema)
        except (JsonSchemaError, JsonValidationError, ValueError) as exc:
            raise error_type(
                "node payload does not satisfy its declared contract",
                execution_id=execution_id,
                node_id=node_id,
            ) from exc


__all__ = [
    "ArtifactExecutionMismatchError",
    "GraphClockError",
    "GraphCycleExecutionError",
    "GraphEventConstructionError",
    "GraphExecutionError",
    "GraphExecutionResult",
    "GraphExecutor",
    "NodeContractNotFoundError",
    "NodeInputValidationError",
    "NodeOutputValidationError",
    "UnknownCurrentNodeError",
]
