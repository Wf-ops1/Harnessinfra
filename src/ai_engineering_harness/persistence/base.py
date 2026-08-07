"""Public contracts for durable execution state storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from ai_engineering_harness.contracts.events import ExecutionEvent
from ai_engineering_harness.contracts.execution import ExecutionRecord


class StateStorageError(Exception):
    """Base class for fail-closed state storage failures."""

    def __init__(self, message: str, *, execution_id: str | None = None) -> None:
        super().__init__(message)
        self.execution_id = execution_id


class ExecutionAlreadyExistsError(StateStorageError):
    """Creation was refused because managed state already exists."""


class ExecutionNotFoundError(StateStorageError):
    """No managed execution record exists for the requested identity."""


class RevisionConflictError(StateStorageError):
    """Optimistic concurrency rejected a stale or invalid revision."""

    def __init__(
        self,
        execution_id: str,
        *,
        expected_revision: int,
        actual_revision: int,
    ) -> None:
        super().__init__(
            (
                f"revision conflict for {execution_id!r}: expected "
                f"{expected_revision}, found {actual_revision}"
            ),
            execution_id=execution_id,
        )
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision


class ExecutionIdentityMismatchError(StateStorageError):
    """A replacement attempted to change immutable execution identity."""


class StateIntegrityError(StateStorageError):
    """Persisted execution state is malformed or noncanonical."""


class JournalIntegrityError(StateIntegrityError):
    """The canonical event journal or its hash chain is invalid."""


class DuplicateEventError(JournalIntegrityError):
    """An event identifier already exists in the canonical journal."""


class LockAcquisitionTimeoutError(StateStorageError):
    """The cross-process lock was not acquired before its deadline."""


class LockOwnershipError(StateStorageError):
    """A lock handle is forged, foreign, inactive, or used incorrectly."""


class LockUnavailableError(StateStorageError):
    """The operating system cannot provide the required file lock."""


class RecoveryConflictError(StateIntegrityError):
    """Crash recovery is ambiguous or would discard integrity evidence."""


class StateWriteError(StateStorageError):
    """Durable state could not be published atomically."""


@dataclass(frozen=True, slots=True)
class ExecutionLock:
    """Immutable public handle for one active cross-process lock."""

    lock_id: str
    execution_id: str
    owner_id: str
    fencing_token: int
    acquired_at: datetime


@runtime_checkable
class StateStorageProvider(Protocol):
    """Stable provider boundary for resumable execution state."""

    def create_execution(self, record: ExecutionRecord) -> ExecutionRecord:
        """Create revision zero without overwriting managed state."""

    def load_execution(
        self,
        execution_id: str,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionRecord:
        """Load one canonical execution record."""

    def compare_and_set_execution(
        self,
        execution_id: str,
        expected_revision: int,
        replacement: ExecutionRecord,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionRecord:
        """Publish exactly the next revision when the expected revision matches."""

    def append_event(
        self,
        execution_id: str,
        event: ExecutionEvent,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionEvent:
        """Atomically append one canonical, hash-chained event."""

    def list_executions(self) -> tuple[ExecutionRecord, ...]:
        """Return managed records ordered by execution identifier."""

    def acquire_execution_lock(
        self,
        execution_id: str,
        owner_id: str,
        *,
        timeout_seconds: float,
    ) -> ExecutionLock:
        """Acquire an OS-backed lock and advance its durable fencing token."""

    def release_execution_lock(self, lock: ExecutionLock) -> None:
        """Release an active handle owned by this provider instance."""


@runtime_checkable
class EventJournalStateStorageProvider(StateStorageProvider, Protocol):
    """Add canonical journal reads without expanding the F2.2 provider."""

    def load_events(
        self,
        execution_id: str,
        *,
        lock: ExecutionLock | None = None,
    ) -> tuple[ExecutionEvent, ...]:
        """Load the complete canonical journal after fail-closed recovery."""


__all__ = [
    "DuplicateEventError",
    "EventJournalStateStorageProvider",
    "ExecutionAlreadyExistsError",
    "ExecutionIdentityMismatchError",
    "ExecutionLock",
    "ExecutionNotFoundError",
    "JournalIntegrityError",
    "LockAcquisitionTimeoutError",
    "LockOwnershipError",
    "LockUnavailableError",
    "RecoveryConflictError",
    "RevisionConflictError",
    "StateIntegrityError",
    "StateStorageError",
    "StateStorageProvider",
    "StateWriteError",
]
