"""Atomic file persistence for resumable execution state."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from ai_engineering_harness.contracts.events import ExecutionEvent
from ai_engineering_harness.contracts.execution import (
    ExecutionRecord,
    validate_execution_id,
)

from .base import (
    DuplicateEventError,
    ExecutionAlreadyExistsError,
    ExecutionIdentityMismatchError,
    ExecutionLock,
    ExecutionNotFoundError,
    JournalIntegrityError,
    RecoveryConflictError,
    RevisionConflictError,
    StateIntegrityError,
    StateStorageProvider,
    StateWriteError,
)
from .locks import CrossProcessLockManager

_EXECUTION_RECORD_NAME: Final = "execution.json"
_EVENT_JOURNAL_NAME: Final = "event-journal.jsonl"
_DEFAULT_LOCK_TIMEOUT_SECONDS: Final = 10.0
_FIRST_EVENT_HASH: Final = "0" * 64
_HASH_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
_IMMUTABLE_IDENTITY_FIELDS: Final = (
    "workflow_name",
    "artifact_digest",
    "base_commit_sha",
    "original_branch",
    "configuration_digest",
    "created_at",
)


class ExecutionRecordStorageError(Exception):
    """Base error retained for the F2.1 snapshot helpers."""


class ExecutionRecordIntegrityError(ExecutionRecordStorageError):
    """A stored F2.1 record is malformed, noncanonical, or misbound."""


class ExecutionRecordWriteError(ExecutionRecordStorageError):
    """An F2.1 execution record could not be published atomically."""


def execution_record_path(project_root: Path, execution_id: str) -> Path:
    """Return the only F2.1/F2.2 storage location for an execution record."""
    validated_id = validate_execution_id(execution_id)
    return (
        project_root
        / ".harness"
        / "state"
        / "executions"
        / validated_id
        / _EXECUTION_RECORD_NAME
    )


def save_execution_record(project_root: Path, record: ExecutionRecord) -> Path:
    """Publish one F2.1 record without changing its unconditional-save contract."""
    destination = execution_record_path(project_root, record.execution_id)
    content = record.canonical_json().encode("utf-8")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        _atomic_replace_bytes(destination, content)
    except OSError as exc:
        raise ExecutionRecordWriteError(f"cannot write execution record: {exc}") from exc
    return destination


def load_execution_record(project_root: Path, execution_id: str) -> ExecutionRecord:
    """Load an F2.1 canonical record without provider recovery semantics."""
    source = execution_record_path(project_root, execution_id)
    try:
        raw_text = source.read_bytes().decode("utf-8")
    except FileNotFoundError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ExecutionRecordIntegrityError(f"cannot read execution record: {exc}") from exc

    try:
        record = ExecutionRecord.model_validate_json(raw_text)
    except (ValidationError, ValueError) as exc:
        raise ExecutionRecordIntegrityError(f"execution record is invalid: {exc}") from exc

    if record.execution_id != execution_id:
        raise ExecutionRecordIntegrityError(
            "stored execution_id does not match the requested execution"
        )
    if raw_text != record.canonical_json():
        raise ExecutionRecordIntegrityError("execution record is not canonical JSON")
    return record


class AtomicFileStateStorage(StateStorageProvider):
    """OS-locked, compare-and-set state storage rooted in one project."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self._execution_root = (
            self.project_root / ".harness" / "state" / "executions"
        )
        self._locks = CrossProcessLockManager(self.project_root)
        self._owner_id = f"atomic-file-provider-{uuid.uuid4().hex}"

    def create_execution(self, record: ExecutionRecord) -> ExecutionRecord:
        """Create revision zero exactly once under catalog then execution lock."""
        if not isinstance(record, ExecutionRecord):
            raise StateIntegrityError("record must be an ExecutionRecord")
        execution_id = self._validate_execution_id(record.execution_id)
        if record.revision != 0:
            raise RevisionConflictError(
                execution_id,
                expected_revision=0,
                actual_revision=record.revision,
            )

        catalog_lock = self._locks.acquire_catalog(
            self._owner_id,
            timeout_seconds=_DEFAULT_LOCK_TIMEOUT_SECONDS,
        )
        try:
            execution_lock = self.acquire_execution_lock(
                execution_id,
                self._owner_id,
                timeout_seconds=_DEFAULT_LOCK_TIMEOUT_SECONDS,
            )
            try:
                destination = self._record_path(execution_id)
                recovered = self._recover_record(execution_id)
                if recovered is not None or destination.exists():
                    raise ExecutionAlreadyExistsError(
                        f"execution {execution_id!r} already exists",
                        execution_id=execution_id,
                    )
                self._ensure_execution_directory(execution_id)
                self._publish_state_bytes(
                    destination,
                    record.canonical_json().encode("utf-8"),
                    execution_id=execution_id,
                )
                return record
            finally:
                self.release_execution_lock(execution_lock)
        finally:
            self._locks.release_catalog(catalog_lock)

    def load_execution(
        self,
        execution_id: str,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionRecord:
        """Recover and load one canonical record under its execution lock."""
        validated_id = self._validate_execution_id(execution_id)
        with self._execution_guard(validated_id, lock):
            record = self._recover_record(validated_id)
            if record is None:
                raise ExecutionNotFoundError(
                    f"execution {validated_id!r} does not exist",
                    execution_id=validated_id,
                )
            return record

    def compare_and_set_execution(
        self,
        execution_id: str,
        expected_revision: int,
        replacement: ExecutionRecord,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionRecord:
        """Publish only the exact next revision while preserving identity."""
        validated_id = self._validate_execution_id(execution_id)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 0
        ):
            raise StateIntegrityError(
                "expected_revision must be a non-negative integer",
                execution_id=validated_id,
            )
        if not isinstance(replacement, ExecutionRecord):
            raise StateIntegrityError(
                "replacement must be an ExecutionRecord",
                execution_id=validated_id,
            )

        with self._execution_guard(validated_id, lock):
            current = self._recover_record(validated_id)
            if current is None:
                raise ExecutionNotFoundError(
                    f"execution {validated_id!r} does not exist",
                    execution_id=validated_id,
                )
            if current.revision != expected_revision:
                raise RevisionConflictError(
                    validated_id,
                    expected_revision=expected_revision,
                    actual_revision=current.revision,
                )
            required_revision = expected_revision + 1
            if replacement.revision != required_revision:
                raise RevisionConflictError(
                    validated_id,
                    expected_revision=required_revision,
                    actual_revision=replacement.revision,
                )
            self._validate_replacement_identity(validated_id, current, replacement)
            self._publish_state_bytes(
                self._record_path(validated_id),
                replacement.canonical_json().encode("utf-8"),
                execution_id=validated_id,
            )
            return replacement

    def append_event(
        self,
        execution_id: str,
        event: ExecutionEvent,
        *,
        lock: ExecutionLock | None = None,
    ) -> ExecutionEvent:
        """Republish the complete journal with one canonical hash-chained event."""
        validated_id = self._validate_execution_id(execution_id)
        if not isinstance(event, ExecutionEvent):
            raise JournalIntegrityError(
                "event must be an ExecutionEvent",
                execution_id=validated_id,
            )
        if event.execution_id != validated_id:
            raise ExecutionIdentityMismatchError(
                "event execution_id does not match the requested execution",
                execution_id=validated_id,
            )
        if event.previous_hash is not None or event.current_hash is not None:
            raise JournalIntegrityError(
                "caller-supplied event hashes must both be null",
                execution_id=validated_id,
            )

        with self._execution_guard(validated_id, lock):
            if self._recover_record(validated_id) is None:
                raise ExecutionNotFoundError(
                    f"execution {validated_id!r} does not exist",
                    execution_id=validated_id,
                )
            journal_bytes, events = self._recover_journal(validated_id)
            if any(existing.event_id == event.event_id for existing in events):
                raise DuplicateEventError(
                    f"event_id {event.event_id!r} already exists",
                    execution_id=validated_id,
                )
            previous_hash = events[-1].current_hash if events else _FIRST_EVENT_HASH
            assert previous_hash is not None
            with_previous = event.model_copy(update={"previous_hash": previous_hash})
            current_hash = _event_hash(with_previous)
            persisted = ExecutionEvent.model_validate(
                with_previous.model_copy(update={"current_hash": current_hash}).model_dump()
            )
            self._publish_state_bytes(
                self._journal_path(validated_id),
                journal_bytes + _canonical_event_line(persisted),
                execution_id=validated_id,
            )
            return persisted

    def list_executions(self) -> tuple[ExecutionRecord, ...]:
        """Return managed records sorted by ID under the catalog hierarchy."""
        catalog_lock = self._locks.acquire_catalog(
            self._owner_id,
            timeout_seconds=_DEFAULT_LOCK_TIMEOUT_SECONDS,
        )
        try:
            if not self._execution_root.exists():
                return ()
            self._require_confined(self._execution_root)
            if not self._execution_root.is_dir():
                raise StateIntegrityError("execution state root is not a directory")
            try:
                entries = sorted(self._execution_root.iterdir(), key=lambda path: path.name)
            except OSError as exc:
                raise StateIntegrityError(f"cannot enumerate execution state: {exc}") from exc

            records: list[ExecutionRecord] = []
            for entry in entries:
                if not entry.is_dir():
                    continue
                self._require_confined(entry)
                if not self._has_managed_record(entry):
                    continue
                execution_id = self._validate_execution_id(entry.name)
                execution_lock = self.acquire_execution_lock(
                    execution_id,
                    self._owner_id,
                    timeout_seconds=_DEFAULT_LOCK_TIMEOUT_SECONDS,
                )
                try:
                    record = self._recover_record(execution_id)
                    if record is None:
                        raise RecoveryConflictError(
                            "managed execution disappeared during listing",
                            execution_id=execution_id,
                        )
                    records.append(record)
                finally:
                    self.release_execution_lock(execution_lock)
            return tuple(records)
        finally:
            self._locks.release_catalog(catalog_lock)

    def acquire_execution_lock(
        self,
        execution_id: str,
        owner_id: str,
        *,
        timeout_seconds: float,
    ) -> ExecutionLock:
        """Acquire an OS lock and advance its durable fencing token."""
        return self._locks.acquire(
            execution_id,
            owner_id,
            timeout_seconds=timeout_seconds,
        )

    def release_execution_lock(self, lock: ExecutionLock) -> None:
        """Release an exact handle created by this provider instance."""
        self._locks.release(lock)

    @contextmanager
    def _execution_guard(
        self,
        execution_id: str,
        lock: ExecutionLock | None,
    ) -> Iterator[None]:
        if lock is not None:
            self._locks.validate(lock, execution_id)
            yield
            return
        internal = self.acquire_execution_lock(
            execution_id,
            self._owner_id,
            timeout_seconds=_DEFAULT_LOCK_TIMEOUT_SECONDS,
        )
        try:
            yield
        finally:
            self.release_execution_lock(internal)

    def _recover_record(self, execution_id: str) -> ExecutionRecord | None:
        destination = self._record_path(execution_id)
        candidates = self._known_temp_paths(destination)
        if destination.exists():
            try:
                record = self._load_record_path(destination, execution_id)
            except StateIntegrityError as exc:
                raise RecoveryConflictError(
                    "canonical execution record is invalid; recovery refused",
                    execution_id=execution_id,
                ) from exc
            self._remove_known_temps(candidates, execution_id=execution_id)
            return record
        if len(candidates) > 1:
            raise RecoveryConflictError(
                "multiple abandoned execution record candidates exist",
                execution_id=execution_id,
            )
        if not candidates:
            return None

        candidate = candidates[0]
        try:
            record = self._load_record_path(candidate, execution_id)
        except StateIntegrityError as exc:
            raise RecoveryConflictError(
                "abandoned execution record candidate is invalid",
                execution_id=execution_id,
            ) from exc
        try:
            os.replace(candidate, destination)
            _fsync_directory(destination.parent)
        except OSError as exc:
            raise StateWriteError(
                f"cannot recover execution record: {exc}",
                execution_id=execution_id,
            ) from exc
        return record

    def _recover_journal(
        self,
        execution_id: str,
    ) -> tuple[bytes, tuple[ExecutionEvent, ...]]:
        destination = self._journal_path(execution_id)
        candidates = self._known_temp_paths(destination)
        if destination.exists():
            raw, events = self._load_journal_path(destination, execution_id)
            self._remove_known_temps(candidates, execution_id=execution_id)
            return raw, events
        if len(candidates) > 1:
            raise RecoveryConflictError(
                "multiple abandoned event journal candidates exist",
                execution_id=execution_id,
            )
        if not candidates:
            return b"", ()

        candidate = candidates[0]
        try:
            raw, events = self._load_journal_path(candidate, execution_id)
        except JournalIntegrityError as exc:
            raise RecoveryConflictError(
                "abandoned event journal candidate is invalid",
                execution_id=execution_id,
            ) from exc
        try:
            os.replace(candidate, destination)
            _fsync_directory(destination.parent)
        except OSError as exc:
            raise StateWriteError(
                f"cannot recover event journal: {exc}",
                execution_id=execution_id,
            ) from exc
        return raw, events

    def _load_record_path(self, path: Path, execution_id: str) -> ExecutionRecord:
        self._require_confined(path, execution_id=execution_id)
        try:
            raw_text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise StateIntegrityError(
                f"cannot read execution record: {exc}",
                execution_id=execution_id,
            ) from exc
        try:
            record = ExecutionRecord.model_validate_json(raw_text)
        except (ValidationError, ValueError) as exc:
            raise StateIntegrityError(
                f"execution record is invalid: {exc}",
                execution_id=execution_id,
            ) from exc
        if record.execution_id != execution_id:
            raise StateIntegrityError(
                "stored execution_id does not match the requested execution",
                execution_id=execution_id,
            )
        if raw_text != record.canonical_json():
            raise StateIntegrityError(
                "execution record is not canonical JSON",
                execution_id=execution_id,
            )
        return record

    def _load_journal_path(
        self,
        path: Path,
        execution_id: str,
    ) -> tuple[bytes, tuple[ExecutionEvent, ...]]:
        self._require_confined(path, execution_id=execution_id)
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise JournalIntegrityError(
                f"cannot read event journal: {exc}",
                execution_id=execution_id,
            ) from exc
        if not raw:
            return raw, ()
        if not raw.endswith(b"\n") or b"\r" in raw:
            raise JournalIntegrityError(
                "event journal must contain complete LF-terminated lines",
                execution_id=execution_id,
            )

        events: list[ExecutionEvent] = []
        event_ids: set[str] = set()
        expected_previous = _FIRST_EVENT_HASH
        for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
            if not line.endswith("\n") or line == "\n":
                raise JournalIntegrityError(
                    f"event journal line {line_number} is incomplete or empty",
                    execution_id=execution_id,
                )
            try:
                event = ExecutionEvent.model_validate_json(line[:-1])
            except (ValidationError, ValueError) as exc:
                raise JournalIntegrityError(
                    f"event journal line {line_number} is invalid: {exc}",
                    execution_id=execution_id,
                ) from exc
            if _canonical_event_line(event).decode("utf-8") != line:
                raise JournalIntegrityError(
                    f"event journal line {line_number} is not canonical JSON",
                    execution_id=execution_id,
                )
            if event.execution_id != execution_id:
                raise JournalIntegrityError(
                    f"event journal line {line_number} belongs to another execution",
                    execution_id=execution_id,
                )
            if event.event_id in event_ids:
                raise JournalIntegrityError(
                    f"event journal contains duplicate event_id {event.event_id!r}",
                    execution_id=execution_id,
                )
            if (
                event.previous_hash != expected_previous
                or event.current_hash is None
                or _HASH_PATTERN.fullmatch(event.current_hash) is None
                or event.current_hash != _event_hash(event)
            ):
                raise JournalIntegrityError(
                    f"event journal hash chain is invalid at line {line_number}",
                    execution_id=execution_id,
                )
            event_ids.add(event.event_id)
            expected_previous = event.current_hash
            events.append(event)
        return raw, tuple(events)

    def _validate_replacement_identity(
        self,
        execution_id: str,
        current: ExecutionRecord,
        replacement: ExecutionRecord,
    ) -> None:
        if replacement.execution_id != execution_id:
            raise ExecutionIdentityMismatchError(
                "replacement execution_id does not match",
                execution_id=execution_id,
            )
        changed = [
            field
            for field in _IMMUTABLE_IDENTITY_FIELDS
            if getattr(current, field) != getattr(replacement, field)
        ]
        if changed:
            raise ExecutionIdentityMismatchError(
                f"replacement changes immutable identity fields: {', '.join(changed)}",
                execution_id=execution_id,
            )
        if replacement.updated_at < current.updated_at:
            raise ExecutionIdentityMismatchError(
                "replacement updated_at cannot regress",
                execution_id=execution_id,
            )

    def _record_path(self, execution_id: str) -> Path:
        path = execution_record_path(self.project_root, execution_id)
        self._require_confined(path, execution_id=execution_id)
        return path

    def _journal_path(self, execution_id: str) -> Path:
        path = self._record_path(execution_id).with_name(_EVENT_JOURNAL_NAME)
        self._require_confined(path, execution_id=execution_id)
        return path

    def _ensure_execution_directory(self, execution_id: str) -> None:
        directory = self._record_path(execution_id).parent
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StateWriteError(
                f"cannot create execution state directory: {exc}",
                execution_id=execution_id,
            ) from exc
        self._require_confined(directory, execution_id=execution_id)

    def _publish_state_bytes(
        self,
        destination: Path,
        content: bytes,
        *,
        execution_id: str,
    ) -> None:
        self._ensure_execution_directory(execution_id)
        self._require_confined(destination, execution_id=execution_id)
        try:
            _atomic_replace_bytes(destination, content)
        except OSError as exc:
            raise StateWriteError(
                f"cannot publish execution state: {exc}",
                execution_id=execution_id,
            ) from exc

    def _known_temp_paths(self, destination: Path) -> tuple[Path, ...]:
        if not destination.parent.exists():
            return ()
        self._require_confined(destination.parent)
        try:
            candidates = tuple(
                sorted(
                    destination.parent.glob(f".{destination.name}.*.tmp"),
                    key=lambda path: path.name,
                )
            )
        except OSError as exc:
            raise RecoveryConflictError(f"cannot inspect recovery candidates: {exc}") from exc
        for candidate in candidates:
            self._require_confined(candidate)
        return candidates

    def _remove_known_temps(
        self,
        candidates: tuple[Path, ...],
        *,
        execution_id: str,
    ) -> None:
        for candidate in candidates:
            try:
                candidate.unlink()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise RecoveryConflictError(
                    f"cannot remove abandoned recovery candidate: {exc}",
                    execution_id=execution_id,
                ) from exc

    @staticmethod
    def _has_managed_record(directory: Path) -> bool:
        if (directory / _EXECUTION_RECORD_NAME).exists():
            return True
        return any(directory.glob(f".{_EXECUTION_RECORD_NAME}.*.tmp"))

    def _require_confined(
        self,
        path: Path,
        *,
        execution_id: str | None = None,
    ) -> None:
        try:
            path.resolve(strict=False).relative_to(self.project_root)
        except (OSError, ValueError) as exc:
            raise StateIntegrityError(
                "managed state path escapes the project root",
                execution_id=execution_id,
            ) from exc

    @staticmethod
    def _validate_execution_id(execution_id: str) -> str:
        try:
            return validate_execution_id(execution_id)
        except (TypeError, ValueError) as exc:
            raise StateIntegrityError("execution_id is invalid") from exc


def _canonical_event_json(event: ExecutionEvent, *, include_current_hash: bool) -> bytes:
    exclude = set() if include_current_hash else {"current_hash"}
    try:
        document = event.model_dump(mode="json", exclude=exclude)
        return json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError(f"event cannot be serialized canonically: {exc}") from exc


def _canonical_event_line(event: ExecutionEvent) -> bytes:
    return _canonical_event_json(event, include_current_hash=True) + b"\n"


def _event_hash(event: ExecutionEvent) -> str:
    return hashlib.sha256(
        _canonical_event_json(event, include_current_hash=False)
    ).hexdigest()


def _atomic_replace_bytes(destination: Path, content: bytes) -> None:
    descriptor: int | None = None
    temp_path: Path | None = None
    try:
        descriptor, raw_temp_path = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
        )
        temp_path = Path(raw_temp_path)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, destination)
        temp_path = None
        _fsync_directory(destination.parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "AtomicFileStateStorage",
    "ExecutionRecordIntegrityError",
    "ExecutionRecordStorageError",
    "ExecutionRecordWriteError",
    "execution_record_path",
    "load_execution_record",
    "save_execution_record",
]
