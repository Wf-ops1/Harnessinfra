"""Cross-process file locks with durable fencing tokens."""

from __future__ import annotations

import errno
import math
import os
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from ai_engineering_harness.contracts.execution import validate_execution_id

from .base import (
    ExecutionLock,
    LockAcquisitionTimeoutError,
    LockOwnershipError,
    LockUnavailableError,
    StateIntegrityError,
    StateWriteError,
)

_POLL_INTERVAL_SECONDS: Final = 0.01
_FENCE_SUFFIX: Final = ".fence"
_LOCK_SUFFIX: Final = ".lock"


if sys.platform == "win32":

    def _lock_descriptor_backend(descriptor: int) -> None:
        try:
            from msvcrt import LK_NBLCK, locking
        except ImportError as exc:  # pragma: no cover - platform import failure
            raise OSError(errno.ENOSYS, "msvcrt.locking is unavailable") from exc
        locking(descriptor, LK_NBLCK, 1)


    def _unlock_descriptor_backend(descriptor: int) -> None:
        try:
            from msvcrt import LK_UNLCK, locking
        except ImportError as exc:  # pragma: no cover - platform import failure
            raise OSError(errno.ENOSYS, "msvcrt.locking is unavailable") from exc
        locking(descriptor, LK_UNLCK, 1)

else:

    def _lock_descriptor_backend(descriptor: int) -> None:
        try:
            from fcntl import LOCK_EX, LOCK_NB, flock
        except ImportError as exc:  # pragma: no cover - platform import failure
            raise OSError(errno.ENOSYS, "fcntl.flock is unavailable") from exc
        flock(descriptor, LOCK_EX | LOCK_NB)


    def _unlock_descriptor_backend(descriptor: int) -> None:
        try:
            from fcntl import LOCK_UN, flock
        except ImportError as exc:  # pragma: no cover - platform import failure
            raise OSError(errno.ENOSYS, "fcntl.flock is unavailable") from exc
        flock(descriptor, LOCK_UN)


@dataclass(slots=True)
class _FileLease:
    descriptor: int
    path: Path


@dataclass(frozen=True, slots=True)
class _CatalogLock:
    lock_id: str
    owner_id: str
    acquired_at: datetime


class CrossProcessLockManager:
    """Own active descriptors for one provider instance."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()
        self._lock_root = self._project_root / ".harness" / "state" / "locks"
        self._guard = threading.Lock()
        self._active: dict[str, tuple[ExecutionLock, _FileLease]] = {}
        self._active_by_execution: dict[str, str] = {}
        self._pending: set[str] = set()
        self._catalog_active: tuple[_CatalogLock, _FileLease] | None = None
        self._catalog_pending = False

    def acquire(
        self,
        execution_id: str,
        owner_id: str,
        *,
        timeout_seconds: float,
    ) -> ExecutionLock:
        """Acquire the execution lock and persist a strictly increasing fence."""
        validated_id = self._validate_execution_id(execution_id)
        validated_owner = self._validate_owner(owner_id, execution_id=validated_id)
        timeout = self._validate_timeout(timeout_seconds, execution_id=validated_id)

        with self._guard:
            if (
                validated_id in self._active_by_execution
                or validated_id in self._pending
            ):
                raise LockOwnershipError(
                    f"execution lock {validated_id!r} is not reentrant",
                    execution_id=validated_id,
                )
            self._pending.add(validated_id)

        lease: _FileLease | None = None
        stored = False
        try:
            lock_path = self._lock_root / f"{validated_id}{_LOCK_SUFFIX}"
            lease = self._acquire_file_lock(
                lock_path,
                timeout_seconds=timeout,
                execution_id=validated_id,
            )
            fencing_token = self._advance_fence(validated_id)
            handle = ExecutionLock(
                lock_id=uuid.uuid4().hex,
                execution_id=validated_id,
                owner_id=validated_owner,
                fencing_token=fencing_token,
                acquired_at=datetime.now(UTC),
            )
            with self._guard:
                self._active[handle.lock_id] = (handle, lease)
                self._active_by_execution[validated_id] = handle.lock_id
                self._pending.discard(validated_id)
            stored = True
            return handle
        finally:
            if not stored:
                with self._guard:
                    self._pending.discard(validated_id)
                if lease is not None:
                    self._release_file_lease(lease, suppress_errors=True)

    def validate(self, lock: ExecutionLock, execution_id: str) -> None:
        """Require the exact active object issued by this manager."""
        validated_id = self._validate_execution_id(execution_id)
        if not isinstance(lock, ExecutionLock):
            raise LockOwnershipError(
                "lock handle has an invalid type",
                execution_id=validated_id,
            )
        with self._guard:
            active = self._active.get(lock.lock_id)
            if active is None or active[0] is not lock:
                raise LockOwnershipError(
                    "lock handle is forged, foreign, or no longer active",
                    execution_id=validated_id,
                )
            if lock.execution_id != validated_id:
                raise LockOwnershipError(
                    "lock handle belongs to another execution",
                    execution_id=validated_id,
                )

    def release(self, lock: ExecutionLock) -> None:
        """Release exactly one active handle; repeated release is an error."""
        if not isinstance(lock, ExecutionLock):
            raise LockOwnershipError("lock handle has an invalid type")
        with self._guard:
            active = self._active.get(lock.lock_id)
            if active is None or active[0] is not lock:
                raise LockOwnershipError(
                    "lock handle is forged, foreign, or already released",
                    execution_id=lock.execution_id,
                )
            lease = active[1]

        release_error = self._release_file_lease(lease, suppress_errors=False)
        with self._guard:
            self._active.pop(lock.lock_id, None)
            self._active_by_execution.pop(lock.execution_id, None)
        if release_error is not None:
            raise LockUnavailableError(
                f"cannot release execution lock: {release_error}",
                execution_id=lock.execution_id,
            ) from release_error

    def acquire_catalog(
        self,
        owner_id: str,
        *,
        timeout_seconds: float,
    ) -> _CatalogLock:
        """Acquire the catalog lock used to serialize create and list."""
        validated_owner = self._validate_owner(owner_id)
        timeout = self._validate_timeout(timeout_seconds)
        with self._guard:
            if self._catalog_active is not None or self._catalog_pending:
                raise LockOwnershipError("catalog lock is not reentrant")
            self._catalog_pending = True

        lease: _FileLease | None = None
        stored = False
        try:
            lease = self._acquire_file_lock(
                self._lock_root / ".catalog.lock",
                timeout_seconds=timeout,
                execution_id=None,
            )
            handle = _CatalogLock(
                lock_id=uuid.uuid4().hex,
                owner_id=validated_owner,
                acquired_at=datetime.now(UTC),
            )
            with self._guard:
                self._catalog_active = (handle, lease)
                self._catalog_pending = False
            stored = True
            return handle
        finally:
            if not stored:
                with self._guard:
                    self._catalog_pending = False
                if lease is not None:
                    self._release_file_lease(lease, suppress_errors=True)

    def release_catalog(self, lock: _CatalogLock) -> None:
        """Release the exact active catalog handle."""
        with self._guard:
            active = self._catalog_active
            if active is None or active[0] is not lock:
                raise LockOwnershipError("catalog lock is foreign or already released")
            lease = active[1]
        release_error = self._release_file_lease(lease, suppress_errors=False)
        with self._guard:
            self._catalog_active = None
        if release_error is not None:
            raise LockUnavailableError(
                f"cannot release catalog lock: {release_error}"
            ) from release_error

    def _advance_fence(self, execution_id: str) -> int:
        fence_path = self._lock_root / f"{execution_id}{_FENCE_SUFFIX}"
        self._require_confined(fence_path, execution_id=execution_id)
        try:
            raw = fence_path.read_bytes()
        except FileNotFoundError:
            current = 0
        except OSError as exc:
            raise StateIntegrityError(
                f"cannot read fencing token: {exc}",
                execution_id=execution_id,
            ) from exc
        else:
            try:
                text = raw.decode("ascii")
                current = int(text.removesuffix("\n"))
            except (UnicodeError, ValueError) as exc:
                raise StateIntegrityError(
                    "fencing token is not a canonical positive integer",
                    execution_id=execution_id,
                ) from exc
            if current < 1 or raw != f"{current}\n".encode("ascii"):
                raise StateIntegrityError(
                    "fencing token is not a canonical positive integer",
                    execution_id=execution_id,
                )

        next_token = current + 1
        try:
            _atomic_replace_bytes(fence_path, f"{next_token}\n".encode("ascii"))
        except OSError as exc:
            raise StateWriteError(
                f"cannot publish fencing token: {exc}",
                execution_id=execution_id,
            ) from exc
        return next_token

    def _acquire_file_lock(
        self,
        path: Path,
        *,
        timeout_seconds: float,
        execution_id: str | None,
    ) -> _FileLease:
        try:
            self._require_confined(path, execution_id=execution_id)
            self._lock_root.mkdir(parents=True, exist_ok=True)
            self._require_confined(path, execution_id=execution_id)
            flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            descriptor = os.open(path, flags, 0o600)
        except OSError as exc:
            raise LockUnavailableError(
                f"cannot open OS lock file: {exc}",
                execution_id=execution_id,
            ) from exc

        try:
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            deadline = time.monotonic() + timeout_seconds
            while True:
                try:
                    _try_lock_descriptor(descriptor)
                    return _FileLease(descriptor=descriptor, path=path)
                except OSError as exc:
                    if not _is_lock_contention(exc):
                        raise LockUnavailableError(
                            f"OS file locking is unavailable: {exc}",
                            execution_id=execution_id,
                        ) from exc
                    if time.monotonic() >= deadline:
                        raise LockAcquisitionTimeoutError(
                            f"timed out acquiring lock after {timeout_seconds:g} seconds",
                            execution_id=execution_id,
                        ) from exc
                    time.sleep(
                        min(_POLL_INTERVAL_SECONDS, max(0.0, deadline - time.monotonic()))
                    )
        except Exception:
            os.close(descriptor)
            raise

    def _release_file_lease(
        self,
        lease: _FileLease,
        *,
        suppress_errors: bool,
    ) -> OSError | None:
        error: OSError | None = None
        try:
            _unlock_descriptor(lease.descriptor)
        except OSError as exc:
            error = exc
        try:
            os.close(lease.descriptor)
        except OSError as exc:
            error = error or exc
        if error is not None and not suppress_errors:
            return error
        return None

    def _require_confined(
        self,
        path: Path,
        *,
        execution_id: str | None,
    ) -> None:
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(self._project_root)
        except (OSError, ValueError) as exc:
            raise LockUnavailableError(
                "lock path escapes the project root",
                execution_id=execution_id,
            ) from exc

    @staticmethod
    def _validate_execution_id(execution_id: str) -> str:
        try:
            return validate_execution_id(execution_id)
        except (TypeError, ValueError) as exc:
            raise StateIntegrityError("execution_id is invalid") from exc

    @staticmethod
    def _validate_owner(
        owner_id: str,
        *,
        execution_id: str | None = None,
    ) -> str:
        if (
            type(owner_id) is not str
            or not owner_id
            or owner_id != owner_id.strip()
            or len(owner_id) > 256
        ):
            raise LockOwnershipError(
                "owner_id must be a non-empty canonical string",
                execution_id=execution_id,
            )
        return owner_id

    @staticmethod
    def _validate_timeout(
        timeout_seconds: float,
        *,
        execution_id: str | None = None,
    ) -> float:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds < 0
        ):
            raise LockUnavailableError(
                "timeout_seconds must be finite and non-negative",
                execution_id=execution_id,
            )
        return float(timeout_seconds)


def _try_lock_descriptor(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    _lock_descriptor_backend(descriptor)


def _unlock_descriptor(descriptor: int) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    _unlock_descriptor_backend(descriptor)


def _is_lock_contention(exc: OSError) -> bool:
    if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
        return True
    return getattr(exc, "winerror", None) in {32, 33, 36}


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
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = ["CrossProcessLockManager", "ExecutionLock"]
