"""Atomic file persistence restricted to ``ExecutionRecord`` snapshots."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from ai_engineering_harness.contracts.execution import (
    ExecutionRecord,
    validate_execution_id,
)

_EXECUTION_RECORD_NAME = "execution.json"


class ExecutionRecordStorageError(Exception):
    """Base error for durable execution record storage."""


class ExecutionRecordIntegrityError(ExecutionRecordStorageError):
    """A stored record is malformed, noncanonical, or bound to another execution."""


class ExecutionRecordWriteError(ExecutionRecordStorageError):
    """An execution record could not be published atomically."""


def execution_record_path(project_root: Path, execution_id: str) -> Path:
    """Return the only F2.1 storage location for an execution record."""
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
    """Publish one canonical record without exposing a partial destination file."""
    destination = execution_record_path(project_root, record.execution_id)
    content = record.canonical_json().encode("utf-8")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        _atomic_replace_bytes(destination, content)
    except OSError as exc:
        raise ExecutionRecordWriteError(f"cannot write execution record: {exc}") from exc
    return destination


def load_execution_record(project_root: Path, execution_id: str) -> ExecutionRecord:
    """Load a canonical record and verify its identity before returning it."""
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
    "ExecutionRecordIntegrityError",
    "ExecutionRecordStorageError",
    "ExecutionRecordWriteError",
    "execution_record_path",
    "load_execution_record",
    "save_execution_record",
]
