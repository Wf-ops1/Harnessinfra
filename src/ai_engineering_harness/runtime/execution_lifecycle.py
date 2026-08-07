"""Canonical F2.5 lifecycle for start, resume, approval, cancellation, and views."""

from __future__ import annotations

import math
import re
import subprocess
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ai_engineering_harness.contracts import CompiledGraphArtifact, HumanApprovalNodeSpec
from ai_engineering_harness.contracts.events import ExecutionEvent
from ai_engineering_harness.contracts.execution import (
    EXECUTION_RECORD_SCHEMA_VERSION,
    ApprovalStatus,
    ExecutionId,
    ExecutionRecord,
    ExecutionState,
)
from ai_engineering_harness.core.config import ConfigResolver
from ai_engineering_harness.persistence import (
    ExecutionBundle,
    ExecutionLock,
    ResumeStateStorageProvider,
    canonical_json_digest,
    canonical_json_object,
)

from .graph_executor import (
    GraphExecutionPausedResult,
    GraphExecutionResult,
    GraphExecutor,
)
from .maf_adapter import MAFAdapter
from .node_executors import NodeExecutorRegistry
from .state_machine import VALID_STATE_TRANSITIONS, EventSourcedStateMachine

APPROVAL_REQUESTED: Literal["APPROVAL_REQUESTED"] = "APPROVAL_REQUESTED"
EXECUTION_APPROVED: Literal["EXECUTION_APPROVED"] = "EXECUTION_APPROVED"
APPROVAL_INVALIDATED: Literal["APPROVAL_INVALIDATED"] = "APPROVAL_INVALIDATED"

_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_APPROVAL_EVENT_TYPES = frozenset(
    {APPROVAL_REQUESTED, EXECUTION_APPROVED, APPROVAL_INVALIDATED}
)
_SECRET_KEYS = frozenset(
    {
        "access_key",
        "api_key",
        "credential",
        "password",
        "private_key",
        "secret",
        "token",
    }
)


class ExecutionLifecycleError(Exception):
    """Base class for public F2.5 lifecycle failures."""

    def __init__(self, message: str, *, execution_id: str | None = None) -> None:
        super().__init__(message)
        self.execution_id = execution_id


class ExecutionConfigurationError(ExecutionLifecycleError):
    """Effective configuration is unsafe or cannot be snapshotted exactly."""


class ExecutionApprovalRequiredError(ExecutionLifecycleError):
    """A paused execution has no matching canonical approval."""


class ApprovalSubjectMismatchError(ExecutionLifecycleError):
    """An approval event does not bind to the current immutable subject."""


class ApprovalLifecycleIntegrityError(ExecutionLifecycleError):
    """Approval events and the execution snapshot cannot be reconciled."""


class ExecutionCancellationError(ExecutionLifecycleError):
    """The requested execution cannot be cancelled or resumed."""


class ExecutionGitIdentityError(ExecutionLifecycleError):
    """The immutable starting Git identity could not be established."""


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class ExecutionStatusView(_StrictFrozenModel):
    """Redaction-safe canonical status derived from durable state."""

    execution_id: ExecutionId
    workflow_name: str = Field(min_length=1)
    current_node_id: str = Field(min_length=1)
    current_state: ExecutionState
    approval_status: ApprovalStatus
    revision: int = Field(ge=0)
    updated_at: datetime


class ExecutionInspection(_StrictFrozenModel):
    """Redaction-safe execution identity and journal summary."""

    status: ExecutionStatusView
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    configuration_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    initial_input_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_count: int = Field(ge=0)
    event_types: tuple[str, ...]

    @field_validator("event_types", mode="before")
    @classmethod
    def freeze_event_types(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class ExecutionLifecycleService:
    """Coordinate resumable execution over the canonical provider and FSM."""

    def __init__(
        self,
        project_root: Path,
        storage: ResumeStateStorageProvider,
        executors: NodeExecutorRegistry,
        *,
        config_resolver: ConfigResolver | None = None,
        lock_timeout_seconds: float = 30.0,
        clock: Callable[[], datetime] | None = None,
        execution_id_factory: Callable[[], str] | None = None,
        event_id_factory: Callable[[], str] | None = None,
        owner_id_factory: Callable[[], str] | None = None,
        git_identity_provider: Callable[[], tuple[str, str]] | None = None,
    ) -> None:
        if not isinstance(storage, ResumeStateStorageProvider):
            raise TypeError("storage must implement ResumeStateStorageProvider")
        if not isinstance(executors, NodeExecutorRegistry):
            raise TypeError("executors must be a NodeExecutorRegistry")
        if (
            isinstance(lock_timeout_seconds, bool)
            or not isinstance(lock_timeout_seconds, (int, float))
            or not math.isfinite(lock_timeout_seconds)
            or lock_timeout_seconds < 0
        ):
            raise ValueError("lock_timeout_seconds must be non-negative")
        self.project_root = Path(project_root).resolve()
        self._storage = storage
        self._executors = executors
        self._config_resolver = config_resolver or ConfigResolver(self.project_root)
        self._lock_timeout_seconds = float(lock_timeout_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._execution_id_factory = execution_id_factory or self._default_execution_id
        self._event_id_factory = event_id_factory or (
            lambda: f"lifecycle-event-{uuid.uuid4().hex}"
        )
        self._owner_id_factory = owner_id_factory or (
            lambda: f"execution-lifecycle-{uuid.uuid4().hex}"
        )
        self._git_identity_provider = git_identity_provider or self._read_git_identity
        self._graph_executor = GraphExecutor(
            storage,
            executors,
            resume_enabled=True,
            approval_handler=self,
            lock_timeout_seconds=self._lock_timeout_seconds,
            clock=self._clock,
            event_id_factory=self._event_id_factory,
            owner_id_factory=self._owner_id_factory,
        )

    def start(
        self,
        compiled_artifact_path: Path,
        *,
        initial_input: dict[str, object],
        execution_id: str | None = None,
        profile_name: str = "default",
        cli_overrides: dict[str, object] | None = None,
        configuration: dict[str, object] | None = None,
    ) -> GraphExecutionResult | GraphExecutionPausedResult:
        """Create one exact revision-zero execution and begin traversal."""
        artifact = MAFAdapter.load_and_validate(Path(compiled_artifact_path))
        effective_configuration = (
            configuration
            if configuration is not None
            else self._config_resolver.resolve(
                profile_name=profile_name,
                cli_overrides=cli_overrides,
            )
        )
        self._reject_secret_configuration(effective_configuration)
        try:
            configuration_json = canonical_json_object(effective_configuration)
            initial_input_json = canonical_json_object(initial_input)
        except ValueError as exc:
            raise ExecutionConfigurationError(
                "configuration and initial input must be finite JSON objects"
            ) from exc
        selected_id = execution_id or self._execution_id_factory()
        self._graph_executor.preflight(
            artifact,
            initial_input,
            execution_id=selected_id,
        )
        base_commit_sha, original_branch = self._git_identity_provider()
        self._validate_git_identity(base_commit_sha, original_branch)
        timestamp = self._next_timestamp(datetime.min.replace(tzinfo=UTC))
        artifact_json = artifact.canonical_json()
        bundle = ExecutionBundle(
            bundle_schema_version="1.0",
            execution_id=selected_id,
            artifact_digest=canonical_json_digest(artifact_json),
            configuration_digest=canonical_json_digest(configuration_json),
            initial_input_digest=canonical_json_digest(initial_input_json),
            artifact_json=artifact_json,
            configuration_json=configuration_json,
        )
        record = ExecutionRecord(
            record_schema_version=EXECUTION_RECORD_SCHEMA_VERSION,
            revision=0,
            execution_id=selected_id,
            workflow_name=artifact.graph.graph.name,
            artifact_digest=bundle.artifact_digest,
            base_commit_sha=base_commit_sha,
            original_branch=original_branch,
            worktree_path=None,
            current_node_id=artifact.graph.graph.entrypoint,
            current_state=ExecutionState.INITIATED,
            attempt_by_node={},
            created_at=timestamp,
            updated_at=timestamp,
            configuration_digest=bundle.configuration_digest,
            approval_status=ApprovalStatus.NOT_REQUIRED,
            candidate_commit_sha=None,
            promotion_commit_sha=None,
            failure=None,
        )
        self._storage.create_execution_bundle(bundle, initial_input=initial_input)
        self._storage.create_execution(record)
        return self._graph_executor.execute(artifact, selected_id, initial_input)

    def resume(
        self,
        execution_id: str,
    ) -> GraphExecutionResult | GraphExecutionPausedResult:
        """Resume only from the immutable bundle and canonical journal."""
        record, bundle, artifact = self._prepare_resume(execution_id)
        if record.current_state == ExecutionState.CANCELLED:
            raise ExecutionCancellationError(
                "cancelled execution cannot be resumed",
                execution_id=execution_id,
            )
        if record.current_state == ExecutionState.INITIATED:
            initial_input = self._storage.load_payload(
                execution_id,
                bundle.initial_input_digest,
            )
            return self._graph_executor.execute(
                artifact,
                execution_id,
                initial_input,
            )
        return self._graph_executor.resume(artifact, execution_id)

    def approve(self, execution_id: str, *, approver: str) -> ExecutionRecord:
        """Approve exactly the currently paused immutable subject."""
        if type(approver) is not str or not approver.strip() or approver != approver.strip():
            raise ApprovalSubjectMismatchError(
                "approver must be a non-empty trimmed identifier",
                execution_id=execution_id,
            )
        lock = self._acquire(execution_id)
        try:
            record = self._recover_approval_locked(execution_id, lock)
            machine = self._state_machine(execution_id, lock)
            record = machine.recover(lock=lock)
            if record.current_state != ExecutionState.PAUSED_AWAITING_APPROVAL:
                raise ApprovalSubjectMismatchError(
                    "execution is not paused for approval",
                    execution_id=execution_id,
                )
            bundle = self._storage.load_execution_bundle(execution_id, lock=lock)
            artifact = MAFAdapter.validate_snapshot(
                bundle.artifact_json,
                expected_digest=record.artifact_digest,
            )
            node = self._human_node(artifact, record.current_node_id, execution_id)
            request = self._latest_approval_request(execution_id, lock)
            subject_digest = self._approval_subject_digest(
                record,
                node_id=node.id,
                input_digest=request["input_digest"],
            )
            if request["subject_digest"] != subject_digest:
                raise ApprovalSubjectMismatchError(
                    "approval request does not match the current subject",
                    execution_id=execution_id,
                )
            existing = self._latest_approval_grant(execution_id, lock)
            if record.approval_status == ApprovalStatus.APPROVED:
                if existing is None or existing["approver"] != approver:
                    raise ApprovalSubjectMismatchError(
                        "execution was approved by a different approver",
                        execution_id=execution_id,
                    )
                return record
            if record.approval_status != ApprovalStatus.PENDING:
                raise ApprovalSubjectMismatchError(
                    "execution approval status is not pending",
                    execution_id=execution_id,
                )
            timestamp = self._next_timestamp(record.updated_at)
            target_revision = record.revision + 1
            self._append_lifecycle_event(
                execution_id,
                EXECUTION_APPROVED,
                {
                    "approver": approver,
                    "fencing_token": lock.fencing_token,
                    "node_id": node.id,
                    "record_revision": target_revision,
                    "subject_digest": subject_digest,
                },
                timestamp=timestamp,
                lock=lock,
            )
            replacement = self._approval_replacement(
                record,
                status=ApprovalStatus.APPROVED,
                revision=target_revision,
                updated_at=timestamp,
            )
            return self._storage.compare_and_set_execution(
                execution_id,
                record.revision,
                replacement,
                lock=lock,
            )
        finally:
            self._storage.release_execution_lock(lock)

    def cancel(self, execution_id: str) -> ExecutionRecord:
        """Transition a cancelable execution to the final CANCELLED state."""
        lock = self._acquire(execution_id)
        try:
            record = self._recover_approval_locked(execution_id, lock)
            machine = self._state_machine(execution_id, lock)
            record = machine.recover(lock=lock)
            if record.current_state == ExecutionState.CANCELLED:
                return record
            if not VALID_STATE_TRANSITIONS[record.current_state] or (
                ExecutionState.CANCELLED
                not in VALID_STATE_TRANSITIONS[record.current_state]
            ):
                raise ExecutionCancellationError(
                    "execution state cannot transition to CANCELLED",
                    execution_id=execution_id,
                )
            if record.approval_status in {
                ApprovalStatus.PENDING,
                ApprovalStatus.APPROVED,
            }:
                request = self._latest_approval_request(execution_id, lock)
                timestamp = self._next_timestamp(record.updated_at)
                target_revision = record.revision + 1
                self._append_lifecycle_event(
                    execution_id,
                    APPROVAL_INVALIDATED,
                    {
                        "fencing_token": lock.fencing_token,
                        "node_id": request["node_id"],
                        "reason": "execution_cancelled",
                        "record_revision": target_revision,
                        "subject_digest": request["subject_digest"],
                    },
                    timestamp=timestamp,
                    lock=lock,
                )
                record = self._storage.compare_and_set_execution(
                    execution_id,
                    record.revision,
                    self._approval_replacement(
                        record,
                        status=ApprovalStatus.INVALIDATED,
                        revision=target_revision,
                        updated_at=timestamp,
                    ),
                    lock=lock,
                )
            return machine.transition_to(
                ExecutionState.CANCELLED,
                node_id=record.current_node_id,
                attempt=record.attempt_by_node.get(record.current_node_id, 0),
                reason="execution_cancelled",
                lock=lock,
            )
        finally:
            self._storage.release_execution_lock(lock)

    def status(self, execution_id: str) -> ExecutionStatusView:
        """Return a redaction-safe canonical execution status."""
        record = self._load_recovered_record(execution_id)
        return self._status_view(record)

    def inspect(self, execution_id: str) -> ExecutionInspection:
        """Return canonical identity and event metadata without payload content."""
        lock = self._acquire(execution_id)
        try:
            record = self._recover_approval_locked(execution_id, lock)
            record = self._state_machine(execution_id, lock).recover(lock=lock)
            bundle = self._storage.load_execution_bundle(execution_id, lock=lock)
            events = self._storage.load_events(execution_id, lock=lock)
            return ExecutionInspection(
                status=self._status_view(record),
                artifact_digest=bundle.artifact_digest,
                configuration_digest=bundle.configuration_digest,
                initial_input_digest=bundle.initial_input_digest,
                event_count=len(events),
                event_types=tuple(event.event_type for event in events),
            )
        finally:
            self._storage.release_execution_lock(lock)

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
        """Persist an approval request and pause under the executor's lock."""
        current = self._recover_approval_locked(record.execution_id, lock)
        if current.revision != record.revision or current.current_node_id != node.id:
            raise ApprovalLifecycleIntegrityError(
                "approval pause snapshot changed under lock",
                execution_id=record.execution_id,
            )
        if current.current_state != ExecutionState.EXECUTING:
            raise ApprovalLifecycleIntegrityError(
                "approval pause requires EXECUTING state",
                execution_id=record.execution_id,
            )
        artifact_digest = canonical_json_digest(artifact.canonical_json())
        if artifact_digest != current.artifact_digest:
            raise ApprovalSubjectMismatchError(
                "approval artifact does not match the execution",
                execution_id=record.execution_id,
            )
        subject_digest = self._approval_subject_digest(
            current,
            node_id=node.id,
            input_digest=input_digest,
        )
        timestamp = self._next_timestamp(current.updated_at)
        target_revision = current.revision + 1
        self._append_lifecycle_event(
            current.execution_id,
            APPROVAL_REQUESTED,
            {
                "fencing_token": lock.fencing_token,
                "input_digest": input_digest,
                "node_id": node.id,
                "record_revision": target_revision,
                "subject_digest": subject_digest,
            },
            timestamp=timestamp,
            lock=lock,
        )
        current = self._storage.compare_and_set_execution(
            current.execution_id,
            current.revision,
            self._approval_replacement(
                current,
                status=ApprovalStatus.PENDING,
                revision=target_revision,
                updated_at=timestamp,
            ),
            lock=lock,
        )
        current = self._state_machine(current.execution_id, lock).transition_to(
            ExecutionState.PAUSED_AWAITING_APPROVAL,
            node_id=node.id,
            attempt=current.attempt_by_node.get(node.id, 0) + 1,
            reason="human_approval_requested",
            lock=lock,
        )
        return GraphExecutionPausedResult(
            execution_id=current.execution_id,
            node_id=node.id,
            approval_subject_digest=subject_digest,
            executed_node_ids=executed_node_ids,
            final_revision=current.revision,
            fencing_token=lock.fencing_token,
        )

    def is_approval_granted(
        self,
        *,
        record: ExecutionRecord,
        node: HumanApprovalNodeSpec,
        input_digest: str,
        lock: ExecutionLock,
    ) -> bool:
        """Check a grant against the exact current subject without mutating state."""
        if record.approval_status != ApprovalStatus.APPROVED:
            return False
        request = self._latest_approval_request(record.execution_id, lock)
        grant = self._latest_approval_grant(record.execution_id, lock)
        if grant is None:
            return False
        subject = self._approval_subject_digest(
            record,
            node_id=node.id,
            input_digest=input_digest,
        )
        return bool(
            request["node_id"] == node.id
            and request["input_digest"] == input_digest
            and request["subject_digest"] == subject
            and grant["node_id"] == node.id
            and grant["subject_digest"] == subject
        )

    def _prepare_resume(
        self,
        execution_id: str,
    ) -> tuple[ExecutionRecord, ExecutionBundle, CompiledGraphArtifact]:
        lock = self._acquire(execution_id)
        try:
            record = self._recover_approval_locked(execution_id, lock)
            machine = self._state_machine(execution_id, lock)
            record = machine.recover(lock=lock)
            bundle = self._storage.load_execution_bundle(execution_id, lock=lock)
            artifact = MAFAdapter.validate_snapshot(
                bundle.artifact_json,
                expected_digest=record.artifact_digest,
            )
            if bundle.configuration_digest != record.configuration_digest:
                raise ExecutionConfigurationError(
                    "stored configuration digest does not match the execution",
                    execution_id=execution_id,
                )
            if record.current_state == ExecutionState.EXECUTING and (
                record.approval_status == ApprovalStatus.PENDING
            ):
                node = self._human_node(artifact, record.current_node_id, execution_id)
                record = machine.transition_to(
                    ExecutionState.PAUSED_AWAITING_APPROVAL,
                    node_id=node.id,
                    attempt=record.attempt_by_node.get(node.id, 0) + 1,
                    reason="human_approval_requested",
                    lock=lock,
                )
            if record.current_state == ExecutionState.PAUSED_AWAITING_APPROVAL:
                if record.approval_status != ApprovalStatus.APPROVED:
                    raise ExecutionApprovalRequiredError(
                        "execution requires canonical approval before resume",
                        execution_id=execution_id,
                    )
                record = machine.transition_to(
                    ExecutionState.EXECUTING,
                    node_id=record.current_node_id,
                    attempt=record.attempt_by_node.get(record.current_node_id, 0) + 1,
                    reason="human_approval_resumed",
                    lock=lock,
                )
            return record, bundle, artifact
        finally:
            self._storage.release_execution_lock(lock)

    def _load_recovered_record(self, execution_id: str) -> ExecutionRecord:
        lock = self._acquire(execution_id)
        try:
            self._recover_approval_locked(execution_id, lock)
            return self._state_machine(execution_id, lock).recover(lock=lock)
        finally:
            self._storage.release_execution_lock(lock)

    def _recover_approval_locked(
        self,
        execution_id: str,
        lock: ExecutionLock,
    ) -> ExecutionRecord:
        record = self._storage.load_execution(execution_id, lock=lock)
        status = ApprovalStatus.NOT_REQUIRED
        committed_status = ApprovalStatus.NOT_REQUIRED
        active_subject: str | None = None
        active_node: str | None = None
        last_revision = -1
        last_fencing_token = 0
        pending: tuple[ExecutionEvent, ApprovalStatus] | None = None
        saw_event = False
        for event in self._storage.load_events(execution_id, lock=lock):
            if event.event_type not in _APPROVAL_EVENT_TYPES:
                continue
            saw_event = True
            payload = event.payload
            if event.event_type == APPROVAL_REQUESTED:
                expected_keys = {
                    "fencing_token",
                    "input_digest",
                    "node_id",
                    "record_revision",
                    "subject_digest",
                }
                if set(payload) != expected_keys or status not in {
                    ApprovalStatus.NOT_REQUIRED,
                    ApprovalStatus.APPROVED,
                    ApprovalStatus.INVALIDATED,
                }:
                    raise ApprovalLifecycleIntegrityError(
                        "approval request history is invalid",
                        execution_id=execution_id,
                    )
                self._require_digest(payload["input_digest"], execution_id)
                active_subject = self._require_digest(
                    payload["subject_digest"], execution_id
                )
                active_node = self._require_string(payload["node_id"], execution_id)
                next_status = ApprovalStatus.PENDING
            elif event.event_type == EXECUTION_APPROVED:
                expected_keys = {
                    "approver",
                    "fencing_token",
                    "node_id",
                    "record_revision",
                    "subject_digest",
                }
                if set(payload) != expected_keys or status != ApprovalStatus.PENDING:
                    raise ApprovalLifecycleIntegrityError(
                        "approval grant history is invalid",
                        execution_id=execution_id,
                    )
                self._require_string(payload["approver"], execution_id)
                subject = self._require_digest(payload["subject_digest"], execution_id)
                node_id = self._require_string(payload["node_id"], execution_id)
                if subject != active_subject or node_id != active_node:
                    raise ApprovalSubjectMismatchError(
                        "approval grant subject does not match its request",
                        execution_id=execution_id,
                    )
                next_status = ApprovalStatus.APPROVED
            else:
                expected_keys = {
                    "fencing_token",
                    "node_id",
                    "reason",
                    "record_revision",
                    "subject_digest",
                }
                if set(payload) != expected_keys or status not in {
                    ApprovalStatus.PENDING,
                    ApprovalStatus.APPROVED,
                }:
                    raise ApprovalLifecycleIntegrityError(
                        "approval invalidation history is invalid",
                        execution_id=execution_id,
                    )
                if payload["reason"] != "execution_cancelled":
                    raise ApprovalLifecycleIntegrityError(
                        "approval invalidation reason is invalid",
                        execution_id=execution_id,
                    )
                subject = self._require_digest(payload["subject_digest"], execution_id)
                node_id = self._require_string(payload["node_id"], execution_id)
                if subject != active_subject or node_id != active_node:
                    raise ApprovalSubjectMismatchError(
                        "approval invalidation subject does not match",
                        execution_id=execution_id,
                    )
                next_status = ApprovalStatus.INVALIDATED
            revision = self._require_integer(
                payload["record_revision"], execution_id, minimum=1
            )
            fencing_token = self._require_integer(
                payload["fencing_token"], execution_id, minimum=1
            )
            if revision <= last_revision or fencing_token <= last_fencing_token:
                raise ApprovalLifecycleIntegrityError(
                    "approval revisions and fencing tokens must increase strictly",
                    execution_id=execution_id,
                )
            status = next_status
            last_revision = revision
            last_fencing_token = fencing_token
            if revision <= record.revision:
                if pending is not None:
                    raise ApprovalLifecycleIntegrityError(
                        "committed approval event follows a pending event",
                        execution_id=execution_id,
                    )
                committed_status = next_status
            else:
                if pending is not None or revision != record.revision + 1:
                    raise ApprovalLifecycleIntegrityError(
                        "approval event is not the next recoverable revision",
                        execution_id=execution_id,
                    )
                pending = (event, next_status)

        if not saw_event:
            if record.approval_status != ApprovalStatus.NOT_REQUIRED:
                raise ApprovalLifecycleIntegrityError(
                    "approval status has no canonical event history",
                    execution_id=execution_id,
                )
            return record
        if committed_status != record.approval_status:
            raise ApprovalLifecycleIntegrityError(
                "approval snapshot does not match committed event history",
                execution_id=execution_id,
            )
        if pending is None:
            return record
        event, next_status = pending
        replacement = self._approval_replacement(
            record,
            status=next_status,
            revision=record.revision + 1,
            updated_at=event.timestamp,
        )
        return self._storage.compare_and_set_execution(
            execution_id,
            record.revision,
            replacement,
            lock=lock,
        )

    def _latest_approval_request(
        self,
        execution_id: str,
        lock: ExecutionLock,
    ) -> Mapping[str, object]:
        requests = [
            event.payload
            for event in self._storage.load_events(execution_id, lock=lock)
            if event.event_type == APPROVAL_REQUESTED
        ]
        if not requests:
            raise ApprovalLifecycleIntegrityError(
                "approval request event is missing",
                execution_id=execution_id,
            )
        return requests[-1]

    def _latest_approval_grant(
        self,
        execution_id: str,
        lock: ExecutionLock,
    ) -> Mapping[str, object] | None:
        grants = [
            event.payload
            for event in self._storage.load_events(execution_id, lock=lock)
            if event.event_type == EXECUTION_APPROVED
        ]
        return grants[-1] if grants else None

    def _append_lifecycle_event(
        self,
        execution_id: str,
        event_type: Literal[
            "APPROVAL_REQUESTED",
            "EXECUTION_APPROVED",
            "APPROVAL_INVALIDATED",
        ],
        payload: dict[str, object],
        *,
        timestamp: datetime,
        lock: ExecutionLock,
    ) -> ExecutionEvent:
        try:
            event = ExecutionEvent(
                event_id=self._event_id_factory(),
                execution_id=execution_id,
                event_type=event_type,
                timestamp=timestamp,
                payload=payload,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise ApprovalLifecycleIntegrityError(
                "cannot construct a canonical lifecycle event",
                execution_id=execution_id,
            ) from exc
        return self._storage.append_event(execution_id, event, lock=lock)

    def _state_machine(
        self,
        execution_id: str,
        lock: ExecutionLock,
    ) -> EventSourcedStateMachine:
        return EventSourcedStateMachine(
            self._storage,
            execution_id,
            lock_timeout_seconds=self._lock_timeout_seconds,
            clock=self._clock,
            event_id_factory=self._event_id_factory,
            owner_id_factory=self._owner_id_factory,
            lock=lock,
        )

    def _acquire(self, execution_id: str) -> ExecutionLock:
        return self._storage.acquire_execution_lock(
            execution_id,
            self._owner_id_factory(),
            timeout_seconds=self._lock_timeout_seconds,
        )

    def _next_timestamp(self, minimum: datetime) -> datetime:
        observed = self._clock()
        if (
            not isinstance(observed, datetime)
            or observed.tzinfo is None
            or observed.utcoffset() is None
            or observed.utcoffset() != timedelta(0)
            or observed < minimum
        ):
            raise ExecutionLifecycleError(
                "lifecycle clock must be UTC and cannot regress"
            )
        return observed.astimezone(UTC)

    @staticmethod
    def _approval_replacement(
        record: ExecutionRecord,
        *,
        status: ApprovalStatus,
        revision: int,
        updated_at: datetime,
    ) -> ExecutionRecord:
        document = record.model_dump(mode="python")
        document.update(
            {
                "approval_status": status,
                "revision": revision,
                "updated_at": updated_at,
            }
        )
        return ExecutionRecord.model_validate(document)

    @staticmethod
    def _status_view(record: ExecutionRecord) -> ExecutionStatusView:
        return ExecutionStatusView(
            execution_id=record.execution_id,
            workflow_name=record.workflow_name,
            current_node_id=record.current_node_id,
            current_state=record.current_state,
            approval_status=record.approval_status,
            revision=record.revision,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _human_node(
        artifact: CompiledGraphArtifact,
        node_id: str,
        execution_id: str,
    ) -> HumanApprovalNodeSpec:
        node = next((item for item in artifact.graph.nodes if item.id == node_id), None)
        if not isinstance(node, HumanApprovalNodeSpec):
            raise ApprovalSubjectMismatchError(
                "current node is not an explicit human-approval node",
                execution_id=execution_id,
            )
        return node

    @staticmethod
    def _approval_subject_digest(
        record: ExecutionRecord,
        *,
        node_id: str,
        input_digest: object,
    ) -> str:
        digest = ExecutionLifecycleService._require_digest(
            input_digest,
            record.execution_id,
        )
        return canonical_json_digest(
            canonical_json_object(
                {
                    "artifact_digest": record.artifact_digest,
                    "configuration_digest": record.configuration_digest,
                    "execution_id": record.execution_id,
                    "input_digest": digest,
                    "node_id": node_id,
                }
            )
        )

    @staticmethod
    def _reject_secret_configuration(configuration: object) -> None:
        def visit(value: object) -> None:
            if type(value) is dict:
                for raw_key, child in value.items():
                    if type(raw_key) is not str:
                        raise ExecutionConfigurationError(
                            "configuration keys must be strings"
                        )
                    key = raw_key.casefold().replace("-", "_")
                    if key in _SECRET_KEYS or any(
                        key.endswith(f"_{suffix}")
                        for suffix in ("password", "secret", "token")
                    ):
                        raise ExecutionConfigurationError(
                            "raw secret-bearing configuration is unsupported before F5"
                        )
                    visit(child)
            elif type(value) is list:
                for child in value:
                    visit(child)

        visit(configuration)

    def _read_git_identity(self) -> tuple[str, str]:
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ExecutionGitIdentityError(
                "cannot establish starting Git identity"
            ) from exc
        return commit, branch

    @staticmethod
    def _validate_git_identity(commit: str, branch: str) -> None:
        if _GIT_SHA_PATTERN.fullmatch(commit) is None:
            raise ExecutionGitIdentityError("base commit must be a full lowercase Git SHA")
        if type(branch) is not str or not branch.strip() or branch != branch.strip():
            raise ExecutionGitIdentityError("original branch must be non-empty")

    def _default_execution_id(self) -> str:
        timestamp = self._next_timestamp(datetime.min.replace(tzinfo=UTC)).strftime(
            "%Y%m%d%H%M%S"
        )
        return f"exec-{timestamp}-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _require_string(value: object, execution_id: str) -> str:
        if type(value) is not str or not value.strip() or value != value.strip():
            raise ApprovalLifecycleIntegrityError(
                "approval payload string is invalid",
                execution_id=execution_id,
            )
        return value

    @staticmethod
    def _require_digest(value: object, execution_id: str) -> str:
        string = ExecutionLifecycleService._require_string(value, execution_id)
        if _DIGEST_PATTERN.fullmatch(string) is None:
            raise ApprovalLifecycleIntegrityError(
                "approval payload digest is invalid",
                execution_id=execution_id,
            )
        return string

    @staticmethod
    def _require_integer(value: object, execution_id: str, *, minimum: int) -> int:
        if type(value) is not int or value < minimum:
            raise ApprovalLifecycleIntegrityError(
                "approval payload integer is invalid",
                execution_id=execution_id,
            )
        return value


__all__ = [
    "APPROVAL_INVALIDATED",
    "APPROVAL_REQUESTED",
    "EXECUTION_APPROVED",
    "ApprovalLifecycleIntegrityError",
    "ApprovalSubjectMismatchError",
    "ExecutionApprovalRequiredError",
    "ExecutionCancellationError",
    "ExecutionConfigurationError",
    "ExecutionGitIdentityError",
    "ExecutionInspection",
    "ExecutionLifecycleError",
    "ExecutionLifecycleService",
    "ExecutionStatusView",
]
