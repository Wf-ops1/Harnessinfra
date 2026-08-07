"""Canonical traversal of compiled graphs over durable execution state."""

from __future__ import annotations

import hashlib
import math
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, runtime_checkable

from jsonschema import SchemaError as JsonSchemaError
from jsonschema import ValidationError as JsonValidationError
from jsonschema import validate as validate_json_schema
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    CompiledGraphArtifact,
    HumanApprovalNodeSpec,
    NodeSpec,
    ResolvedContractSpec,
    TerminalStateSpec,
)
from ai_engineering_harness.contracts.events import ExecutionEvent
from ai_engineering_harness.contracts.execution import (
    ExecutionId,
    ExecutionRecord,
    ExecutionState,
)
from ai_engineering_harness.persistence import (
    EventJournalStateStorageProvider,
    ExecutionLock,
    ResumeStateStorageProvider,
)

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
from .state_machine import (
    EventSourcedStateMachine,
    InterruptedExecutionError,
    StateReplayError,
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


class InterruptedNodeExecutionError(GraphExecutionError):
    """A started node has no durable outcome and cannot be replayed in F2.5."""

    classification = "requires_intervention"


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


class GraphExecutionPausedResult(_StrictFrozenModel):
    """A graph stopped durably at an explicit human-approval node."""

    execution_id: ExecutionId
    node_id: str = Field(min_length=1)
    approval_subject_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    executed_node_ids: tuple[str, ...]
    final_revision: int = Field(ge=0)
    fencing_token: int = Field(gt=0)

    @field_validator("executed_node_ids", mode="before")
    @classmethod
    def freeze_node_ids(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


@runtime_checkable
class ApprovalPauseHandler(Protocol):
    """Lifecycle boundary used only for explicit human-approval nodes."""

    def pause_for_approval(
        self,
        *,
        artifact: CompiledGraphArtifact,
        record: ExecutionRecord,
        node: HumanApprovalNodeSpec,
        input_digest: str,
        executed_node_ids: tuple[str, ...],
        lock: ExecutionLock,
    ) -> GraphExecutionPausedResult:
        """Persist one approval request and paused execution snapshot."""

    def is_approval_granted(
        self,
        *,
        record: ExecutionRecord,
        node: HumanApprovalNodeSpec,
        input_digest: str,
        lock: ExecutionLock,
    ) -> bool:
        """Return true only for a grant bound to this exact approval subject."""


class GraphExecutor:
    """Execute only nodes and edges declared by a canonical compiled artifact."""

    def __init__(
        self,
        storage: EventJournalStateStorageProvider,
        executors: NodeExecutorRegistry,
        *,
        resume_enabled: bool = False,
        approval_handler: ApprovalPauseHandler | None = None,
        lock_timeout_seconds: float = 30.0,
        clock: Callable[[], datetime] | None = None,
        event_id_factory: Callable[[], str] | None = None,
        owner_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(storage, EventJournalStateStorageProvider):
            raise TypeError(
                "storage must implement EventJournalStateStorageProvider"
            )
        if not isinstance(executors, NodeExecutorRegistry):
            raise TypeError("executors must be a NodeExecutorRegistry")
        if type(resume_enabled) is not bool:
            raise TypeError("resume_enabled must be a bool")
        if resume_enabled and not isinstance(storage, ResumeStateStorageProvider):
            raise TypeError(
                "resume-enabled execution requires ResumeStateStorageProvider"
            )
        if approval_handler is not None and not isinstance(
            approval_handler,
            ApprovalPauseHandler,
        ):
            raise TypeError("approval_handler must implement ApprovalPauseHandler")
        if (
            isinstance(lock_timeout_seconds, bool)
            or not isinstance(lock_timeout_seconds, (int, float))
            or not math.isfinite(lock_timeout_seconds)
            or lock_timeout_seconds < 0
        ):
            raise ValueError("lock_timeout_seconds must be finite and non-negative")
        self._storage = storage
        self._executors = executors
        self._resume_enabled = resume_enabled
        self._approval_handler = approval_handler
        self._lock_timeout_seconds = float(lock_timeout_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._event_id_factory = event_id_factory or (
            lambda: f"event-{uuid.uuid4().hex}"
        )
        self._owner_id_factory = owner_id_factory or (
            lambda: f"graph-executor-{uuid.uuid4().hex}"
        )

    def preflight(
        self,
        artifact: CompiledGraphArtifact,
        initial_input: dict[str, object],
        *,
        execution_id: str = "execution-preflight",
    ) -> None:
        """Validate the entrypoint, initial payload, and executor without mutation."""
        detached = self._detach_artifact(artifact, execution_id=execution_id)
        try:
            payload = _copy_json_object(initial_input, path="initial_input")
        except (TypeError, ValueError) as exc:
            raise NodeInputValidationError(
                "initial input must be a finite JSON object",
                execution_id=execution_id,
            ) from exc
        nodes = {node.id: node for node in detached.graph.nodes}
        entrypoint = detached.graph.graph.entrypoint
        node = nodes.get(entrypoint)
        if node is None:
            raise UnknownCurrentNodeError(
                "graph entrypoint is not an executable node",
                execution_id=execution_id,
                node_id=entrypoint,
            )
        self._validate_node_input(detached, node, payload, execution_id)
        if not (
            isinstance(node, HumanApprovalNodeSpec)
            and self._approval_handler is not None
        ):
            self._executors.select(node).ensure_available()

    def execute(
        self,
        artifact: CompiledGraphArtifact,
        execution_id: str,
        initial_input: dict[str, object],
    ) -> GraphExecutionResult | GraphExecutionPausedResult:
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
                resume_mode=False,
            )
        finally:
            self._storage.release_execution_lock(lock)

    def resume(
        self,
        artifact: CompiledGraphArtifact,
        execution_id: str,
    ) -> GraphExecutionResult | GraphExecutionPausedResult:
        """Recover durable node progress and continue without caller payload."""
        if not self._resume_enabled:
            raise InterruptedNodeExecutionError(
                "graph executor was not configured for resume",
                execution_id=execution_id,
            )
        detached_artifact = self._detach_artifact(artifact, execution_id=execution_id)
        lock = self._storage.acquire_execution_lock(
            execution_id,
            self._owner_id_factory(),
            timeout_seconds=self._lock_timeout_seconds,
        )
        try:
            return self._execute_locked(
                detached_artifact,
                execution_id,
                {},
                lock,
                resume_mode=True,
            )
        finally:
            self._storage.release_execution_lock(lock)

    def _execute_locked(
        self,
        artifact: CompiledGraphArtifact,
        execution_id: str,
        initial_input: dict[str, object],
        lock: ExecutionLock,
        *,
        resume_mode: bool,
    ) -> GraphExecutionResult | GraphExecutionPausedResult:
        nodes = {node.id: node for node in artifact.graph.nodes}
        terminals = {terminal.id: terminal for terminal in artifact.graph.terminal_states}
        record = self._storage.load_execution(execution_id, lock=lock)
        self._validate_execution_identity(record, artifact)
        state_machine = EventSourcedStateMachine(
            self._storage,
            execution_id,
            lock_timeout_seconds=self._lock_timeout_seconds,
            clock=self._clock,
            event_id_factory=self._event_id_factory,
            owner_id_factory=self._owner_id_factory,
            lock=lock,
        )
        record = state_machine.recover(lock=lock)

        if resume_mode:
            current_payload = self._recover_resume_payload(
                artifact,
                record,
                nodes=nodes,
                terminals=terminals,
                lock=lock,
            )
            record = self._storage.load_execution(execution_id, lock=lock)
        else:
            current_payload = initial_input
        visited: set[str] = set()
        executed_node_ids: list[str] = []
        last_failure: NodeExecutionFailure | None = None

        initial_id = record.current_node_id
        initial_terminal = terminals.get(initial_id)
        if initial_terminal is not None:
            expected_state = self._terminal_execution_state(initial_terminal)
            pending_terminal_transition = (
                resume_mode and record.current_state == ExecutionState.EXECUTING
            )
            if record.current_state != expected_state and not pending_terminal_transition:
                raise StateReplayError(
                    "terminal node and execution snapshot state diverge",
                    execution_id=execution_id,
                )
            return self._resolve_terminal(
                artifact,
                record,
                initial_terminal,
                current_payload,
                (),
                None,
                lock,
                state_machine=state_machine if pending_terminal_transition else None,
            )

        initial_node = nodes.get(initial_id)
        if initial_node is None:
            raise UnknownCurrentNodeError(
                f"current node {initial_id!r} is not declared by the artifact",
                execution_id=execution_id,
                node_id=initial_id,
            )
        self._validate_node_input(
            artifact,
            initial_node,
            current_payload,
            execution_id,
        )
        initial_executor = self._executors.select(initial_node)
        if not (
            isinstance(initial_node, HumanApprovalNodeSpec)
            and self._approval_handler is not None
        ):
            initial_executor.ensure_available()
        if resume_mode:
            if record.current_state != ExecutionState.EXECUTING:
                raise InterruptedExecutionError(
                    "resumable nonterminal execution must be EXECUTING",
                    execution_id=execution_id,
                )
        else:
            if (
                record.current_state != ExecutionState.INITIATED
                or initial_id != artifact.graph.graph.entrypoint
            ):
                raise InterruptedExecutionError(
                    "nonterminal execution requires the F2.5 resume contract",
                    execution_id=execution_id,
                )
            initial_attempt = record.attempt_by_node.get(initial_id, 0) + 1
            record = state_machine.transition_to(
                ExecutionState.EXECUTING,
                node_id=initial_id,
                attempt=initial_attempt,
                reason="graph_execution_started",
                lock=lock,
            )

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
                    state_machine=state_machine,
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
            input_digest = self._store_payload(
                execution_id,
                current_payload,
                lock=lock,
            )
            approval_granted = False
            if isinstance(node, HumanApprovalNodeSpec) and self._approval_handler is not None:
                if input_digest is None:
                    raise GraphExecutionError(
                        "approval pause requires durable payload storage",
                        execution_id=execution_id,
                        node_id=node.id,
                    )
                approval_granted = self._approval_handler.is_approval_granted(
                    record=record,
                    node=node,
                    input_digest=input_digest,
                    lock=lock,
                )
            if (
                isinstance(node, HumanApprovalNodeSpec)
                and self._approval_handler is not None
                and not approval_granted
            ):
                if input_digest is None:
                    raise GraphExecutionError(
                        "approval pause requires durable payload storage",
                        execution_id=execution_id,
                        node_id=node.id,
                    )
                return self._approval_handler.pause_for_approval(
                    artifact=artifact,
                    record=record,
                    node=node,
                    input_digest=input_digest,
                    executed_node_ids=tuple(executed_node_ids),
                    lock=lock,
                )
            skip_human_backend = (
                isinstance(node, HumanApprovalNodeSpec)
                and self._approval_handler is not None
                and approval_granted
            )
            if not skip_human_backend:
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
                input_digest=input_digest,
            )

            result = (
                NodeExecutionResult.completed(current_payload)
                if skip_human_backend
                else self._execute_node(executor, context)
            )
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
            output_digest = self._store_payload(
                execution_id,
                result.output,
                lock=lock,
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
                input_digest=input_digest,
                output_digest=output_digest,
                record_revision=record.revision + 1,
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
        *,
        state_machine: EventSourcedStateMachine | None,
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
        final_record = record
        if state_machine is not None:
            final_state = self._terminal_execution_state(terminal)
            final_record = state_machine.transition_to(
                final_state,
                node_id=terminal.id,
                attempt=0,
                reason=(
                    "graph_completed"
                    if final_state == ExecutionState.COMPLETED
                    else "graph_failed"
                ),
                lock=lock,
            )
        return GraphExecutionResult(
            execution_id=record.execution_id,
            terminal_id=terminal.id,
            outcome=terminal.outcome,
            output=terminal_result.output,
            executed_node_ids=executed_node_ids,
            final_revision=final_record.revision,
            fencing_token=lock.fencing_token,
            failure=failure,
        )

    @staticmethod
    def _terminal_execution_state(
        terminal: TerminalStateSpec,
    ) -> ExecutionState:
        if terminal.outcome == "success":
            return ExecutionState.COMPLETED
        return ExecutionState.FAILED

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
        input_digest: str | None = None,
        output_digest: str | None = None,
        record_revision: int | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "attempt": attempt,
            "fencing_token": lock.fencing_token,
            "node_id": node.id,
            "node_type": node.type,
        }
        if next_id is not None:
            payload["next_id"] = next_id
        if input_digest is not None:
            payload["input_digest"] = input_digest
        if output_digest is not None:
            payload["output_digest"] = output_digest
        if record_revision is not None:
            payload["record_revision"] = record_revision
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

    def _store_payload(
        self,
        execution_id: str,
        payload: dict[str, object],
        *,
        lock: ExecutionLock,
    ) -> str | None:
        if not self._resume_enabled:
            return None
        if not isinstance(self._storage, ResumeStateStorageProvider):
            raise GraphExecutionError(
                "resume payload storage is unavailable",
                execution_id=execution_id,
            )
        return self._storage.store_payload(execution_id, payload, lock=lock)

    def _recover_resume_payload(
        self,
        artifact: CompiledGraphArtifact,
        record: ExecutionRecord,
        *,
        nodes: Mapping[str, NodeSpec],
        terminals: Mapping[str, TerminalStateSpec],
        lock: ExecutionLock,
    ) -> dict[str, object]:
        if not isinstance(self._storage, ResumeStateStorageProvider):
            raise InterruptedNodeExecutionError(
                "resume bundle storage is unavailable",
                execution_id=record.execution_id,
            )
        bundle = self._storage.load_execution_bundle(record.execution_id, lock=lock)
        if (
            bundle.artifact_digest != record.artifact_digest
            or bundle.configuration_digest != record.configuration_digest
            or bundle.execution_id != record.execution_id
        ):
            raise ArtifactExecutionMismatchError(
                "resume bundle does not match immutable execution identity",
                execution_id=record.execution_id,
            )
        artifact_digest = "sha256:" + hashlib.sha256(
            artifact.canonical_json().encode("utf-8")
        ).hexdigest()
        if artifact_digest != bundle.artifact_digest:
            raise ArtifactExecutionMismatchError(
                "resume artifact does not match the stored bundle",
                execution_id=record.execution_id,
            )

        expected_node_id = artifact.graph.graph.entrypoint
        expected_payload_digest = bundle.initial_input_digest
        attempts: dict[str, int] = {}
        open_started: tuple[str, int, str, str, int] | None = None
        pending: tuple[ExecutionEvent, str, int, str] | None = None
        last_record_revision = -1
        last_fencing_token = 0
        last_timestamp: datetime | None = None
        last_mutation_revision = 0
        last_global_fencing_token = 0

        for event in self._storage.load_events(record.execution_id, lock=lock):
            payload = event.payload
            if "record_revision" in payload:
                mutation_revision = self._ledger_integer(
                    payload["record_revision"],
                    field="record_revision",
                    minimum=1,
                )
                if mutation_revision != last_mutation_revision + 1:
                    raise InterruptedNodeExecutionError(
                        "durable mutation revisions contain a duplicate or gap",
                        execution_id=record.execution_id,
                    )
                if mutation_revision > record.revision + 1:
                    raise InterruptedNodeExecutionError(
                        "durable mutation revision is beyond recoverable state",
                        execution_id=record.execution_id,
                    )
                last_mutation_revision = mutation_revision
            if "fencing_token" in payload:
                global_fencing_token = self._ledger_integer(
                    payload["fencing_token"],
                    field="fencing_token",
                    minimum=1,
                )
                if global_fencing_token < last_global_fencing_token:
                    raise InterruptedNodeExecutionError(
                        "durable event fencing token regressed",
                        execution_id=record.execution_id,
                    )
                last_global_fencing_token = global_fencing_token
            if event.event_type not in {
                "NODE_STARTED",
                "NODE_COMPLETED",
                "NODE_FAILED",
            }:
                continue
            if last_timestamp is not None and event.timestamp < last_timestamp:
                raise InterruptedNodeExecutionError(
                    "node event timestamps cannot regress",
                    execution_id=record.execution_id,
                )
            last_timestamp = event.timestamp
            if event.event_type == "NODE_STARTED":
                expected_keys = {
                    "attempt",
                    "fencing_token",
                    "input_digest",
                    "node_id",
                    "node_type",
                }
                if set(payload) != expected_keys or open_started is not None:
                    raise InterruptedNodeExecutionError(
                        "node start ledger is malformed or overlapping",
                        execution_id=record.execution_id,
                    )
                node_id = self._ledger_string(payload["node_id"], field="node_id")
                node = nodes.get(node_id)
                if node is None or node_id != expected_node_id:
                    raise InterruptedNodeExecutionError(
                        "node start does not follow the compiled graph",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
                node_type = self._ledger_string(payload["node_type"], field="node_type")
                if node_type != node.type:
                    raise InterruptedNodeExecutionError(
                        "node start type does not match the artifact",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
                attempt = self._ledger_integer(payload["attempt"], field="attempt", minimum=1)
                if attempt != attempts.get(node_id, 0) + 1:
                    raise InterruptedNodeExecutionError(
                        "node attempt is duplicated or non-sequential",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
                fencing_token = self._ledger_integer(
                    payload["fencing_token"],
                    field="fencing_token",
                    minimum=1,
                )
                if fencing_token < last_fencing_token:
                    raise InterruptedNodeExecutionError(
                        "node fencing token regressed",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
                input_digest = self._ledger_digest(payload["input_digest"])
                if input_digest != expected_payload_digest:
                    raise InterruptedNodeExecutionError(
                        "node input digest breaks the durable payload chain",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
                self._storage.load_payload(
                    record.execution_id,
                    input_digest,
                    lock=lock,
                )
                open_started = (
                    node_id,
                    attempt,
                    input_digest,
                    node_type,
                    fencing_token,
                )
                last_fencing_token = fencing_token
                continue

            failed = event.event_type == "NODE_FAILED"
            expected_keys = {
                "attempt",
                "fencing_token",
                "input_digest",
                "next_id",
                "node_id",
                "node_type",
                "output_digest",
                "record_revision",
            }
            if failed:
                expected_keys.update({"error_code", "retryable"})
            if set(payload) != expected_keys or open_started is None:
                raise InterruptedNodeExecutionError(
                    "node outcome ledger is malformed or has no matching start",
                    execution_id=record.execution_id,
                )
            node_id = self._ledger_string(payload["node_id"], field="node_id")
            attempt = self._ledger_integer(payload["attempt"], field="attempt", minimum=1)
            input_digest = self._ledger_digest(payload["input_digest"])
            node_type = self._ledger_string(payload["node_type"], field="node_type")
            fencing_token = self._ledger_integer(
                payload["fencing_token"],
                field="fencing_token",
                minimum=1,
            )
            if (node_id, attempt, input_digest, node_type, fencing_token) != open_started:
                raise InterruptedNodeExecutionError(
                    "node outcome does not match its start event",
                    execution_id=record.execution_id,
                    node_id=node_id,
                )
            next_id = self._ledger_string(payload["next_id"], field="next_id")
            node = nodes[node_id]
            required_next = node.on_failure if failed else node.on_success
            if next_id != required_next or (
                next_id not in nodes and next_id not in terminals
            ):
                raise InterruptedNodeExecutionError(
                    "node outcome does not follow its declared edge",
                    execution_id=record.execution_id,
                    node_id=node_id,
                )
            output_digest = self._ledger_digest(payload["output_digest"])
            self._storage.load_payload(
                record.execution_id,
                output_digest,
                lock=lock,
            )
            target_revision = self._ledger_integer(
                payload["record_revision"],
                field="record_revision",
                minimum=1,
            )
            if target_revision <= last_record_revision:
                raise InterruptedNodeExecutionError(
                    "node outcome revisions must increase strictly",
                    execution_id=record.execution_id,
                    node_id=node_id,
                )
            if failed:
                self._ledger_string(payload["error_code"], field="error_code")
                if type(payload["retryable"]) is not bool:
                    raise InterruptedNodeExecutionError(
                        "retryable must be an exact bool",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
            attempts[node_id] = attempt
            expected_node_id = next_id
            expected_payload_digest = output_digest
            last_record_revision = target_revision
            last_fencing_token = fencing_token
            open_started = None
            if target_revision > record.revision:
                if pending is not None or target_revision != record.revision + 1:
                    raise InterruptedNodeExecutionError(
                        "node ledger contains an invalid pending outcome",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
                pending = (event, node_id, attempt, next_id)

        if open_started is not None:
            raise InterruptedNodeExecutionError(
                "node started without a durable outcome; intervention is required",
                execution_id=record.execution_id,
                node_id=open_started[0],
            )
        for node_id, attempt in attempts.items():
            recorded_attempt = record.attempt_by_node.get(node_id, 0)
            if pending is not None and node_id == pending[1]:
                if recorded_attempt not in {attempt - 1, attempt}:
                    raise InterruptedNodeExecutionError(
                        "pending node attempt diverges from the snapshot",
                        execution_id=record.execution_id,
                        node_id=node_id,
                    )
            elif recorded_attempt != attempt:
                raise InterruptedNodeExecutionError(
                    "committed node attempts diverge from the snapshot",
                    execution_id=record.execution_id,
                    node_id=node_id,
                )

        if pending is not None:
            event, node_id, attempt, next_id = pending
            if record.current_node_id != node_id:
                raise InterruptedNodeExecutionError(
                    "pending outcome does not continue from the snapshot node",
                    execution_id=record.execution_id,
                    node_id=node_id,
                )
            replacement = self._next_record(
                record,
                next_id=next_id,
                node_id=node_id,
                attempt=attempt,
                updated_at=event.timestamp,
            )
            record = self._storage.compare_and_set_execution(
                record.execution_id,
                record.revision,
                replacement,
                lock=lock,
            )
        if record.current_node_id != expected_node_id:
            raise InterruptedNodeExecutionError(
                "node ledger does not reproduce the snapshot current node",
                execution_id=record.execution_id,
                node_id=record.current_node_id,
            )
        return self._storage.load_payload(
            record.execution_id,
            expected_payload_digest,
            lock=lock,
        )

    @staticmethod
    def _ledger_string(value: object, *, field: str) -> str:
        if type(value) is not str or not value.strip() or value != value.strip():
            raise InterruptedNodeExecutionError(
                f"{field} must be a non-empty trimmed string"
            )
        return value

    @staticmethod
    def _ledger_integer(value: object, *, field: str, minimum: int) -> int:
        if type(value) is not int or value < minimum:
            raise InterruptedNodeExecutionError(
                f"{field} must be an integer greater than or equal to {minimum}"
            )
        return value

    @staticmethod
    def _ledger_digest(value: object) -> str:
        digest = GraphExecutor._ledger_string(value, field="digest")
        if len(digest) != 71 or not digest.startswith("sha256:"):
            raise InterruptedNodeExecutionError("digest must be sha256-prefixed")
        try:
            int(digest[7:], 16)
        except ValueError as exc:
            raise InterruptedNodeExecutionError(
                "digest must contain lowercase hexadecimal"
            ) from exc
        if digest[7:] != digest[7:].lower():
            raise InterruptedNodeExecutionError(
                "digest must contain lowercase hexadecimal"
            )
        return digest

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
    "ApprovalPauseHandler",
    "ArtifactExecutionMismatchError",
    "GraphClockError",
    "GraphCycleExecutionError",
    "GraphEventConstructionError",
    "GraphExecutionError",
    "GraphExecutionPausedResult",
    "GraphExecutionResult",
    "GraphExecutor",
    "InterruptedNodeExecutionError",
    "NodeContractNotFoundError",
    "NodeInputValidationError",
    "NodeOutputValidationError",
    "UnknownCurrentNodeError",
]
