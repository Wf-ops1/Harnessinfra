"""Contract and atomic persistence tests for F2.1 execution records."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Self

import pytest
from pydantic import ValidationError

import ai_engineering_harness.persistence.atomic_file as ATOMIC_FILE_MODULE
from ai_engineering_harness.contracts import (
    EXECUTION_RECORD_SCHEMA_VERSION,
    ApprovalStatus,
    ExecutionFailure,
    ExecutionRecord,
    ExecutionState,
)
from ai_engineering_harness.persistence import (
    ExecutionRecordIntegrityError,
    ExecutionRecordWriteError,
    execution_record_path,
    load_execution_record,
    save_execution_record,
)

_CREATED_AT = datetime(2026, 8, 6, 22, 30, tzinfo=UTC)
_UPDATED_AT = datetime(2026, 8, 6, 22, 31, tzinfo=UTC)
_ARTIFACT_DIGEST = f"sha256:{'a' * 64}"
_CONFIGURATION_DIGEST = f"sha256:{'b' * 64}"
_BASE_SHA = "c" * 40


def _record_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "record_schema_version": EXECUTION_RECORD_SCHEMA_VERSION,
        "revision": 0,
        "execution_id": "exec-20260806-abc123",
        "workflow_name": "new-feature",
        "artifact_digest": _ARTIFACT_DIGEST,
        "base_commit_sha": _BASE_SHA,
        "original_branch": "main",
        "worktree_path": None,
        "current_node_id": "analyze_requirements",
        "current_state": ExecutionState.INITIATED,
        "attempt_by_node": {"analyze_requirements": 0},
        "created_at": _CREATED_AT,
        "updated_at": _UPDATED_AT,
        "configuration_digest": _CONFIGURATION_DIGEST,
        "approval_status": ApprovalStatus.NOT_REQUIRED,
        "candidate_commit_sha": None,
        "promotion_commit_sha": None,
        "failure": None,
    }
    data.update(overrides)
    return data


def _record(**overrides: object) -> ExecutionRecord:
    return ExecutionRecord.model_validate(_record_data(**overrides))


def _json_document(record: ExecutionRecord | None = None) -> dict[str, object]:
    return json.loads((record or _record()).canonical_json())


def test_execution_record_has_exact_frozen_field_set() -> None:
    expected = {
        "record_schema_version",
        "revision",
        "execution_id",
        "workflow_name",
        "artifact_digest",
        "base_commit_sha",
        "original_branch",
        "worktree_path",
        "current_node_id",
        "current_state",
        "attempt_by_node",
        "created_at",
        "updated_at",
        "configuration_digest",
        "approval_status",
        "candidate_commit_sha",
        "promotion_commit_sha",
        "failure",
    }

    assert set(ExecutionRecord.model_fields) == expected
    assert ExecutionRecord.model_config["strict"] is True
    assert ExecutionRecord.model_config["frozen"] is True
    assert ExecutionRecord.model_config["extra"] == "forbid"


def test_execution_record_accepts_every_frozen_field() -> None:
    failure = ExecutionFailure(
        code="GATE_FAILED",
        message="Unit tests failed",
        retryable=True,
        node_id="verify",
    )
    record = _record(
        revision=3,
        worktree_path="C:/tmp/harness/exec-20260806-abc123",
        current_state=ExecutionState.FAILED,
        attempt_by_node={"verify": 2, "analyze_requirements": 1},
        approval_status=ApprovalStatus.APPROVED,
        candidate_commit_sha="d" * 40,
        promotion_commit_sha="e" * 40,
        failure=failure,
    )

    assert record.record_schema_version == "1.0"
    assert record.revision == 3
    assert record.attempt_by_node == {"analyze_requirements": 1, "verify": 2}
    assert record.failure == failure


def test_record_and_failure_are_frozen() -> None:
    record = _record(
        failure=ExecutionFailure(
            code="FAILED",
            message="controlled",
            retryable=False,
            node_id=None,
        )
    )

    with pytest.raises(ValidationError, match="frozen_instance"):
        record.revision = 2  # type: ignore[misc]
    assert record.failure is not None
    with pytest.raises(ValidationError, match="frozen_instance"):
        record.failure.message = "changed"  # type: ignore[misc]


def test_attempt_mapping_is_detached_from_caller_and_sorted() -> None:
    attempts = {"verify": 2, "analyze": 1}
    record = _record(attempt_by_node=attempts)
    attempts["analyze"] = 99

    assert record.attempt_by_node == {"analyze": 1, "verify": 2}


def test_canonical_json_is_deterministic_and_round_trips() -> None:
    left = _record(attempt_by_node={"verify": 2, "analyze": 1})
    right = _record(attempt_by_node={"analyze": 1, "verify": 2})

    assert left.canonical_json() == right.canonical_json()
    assert left.canonical_json().endswith("\n")
    assert not left.canonical_json().endswith("\n\n")
    assert ExecutionRecord.model_validate_json(left.canonical_json()) == left


@pytest.mark.parametrize("field_name", sorted(ExecutionRecord.model_fields))
def test_missing_required_field_is_rejected(field_name: str) -> None:
    document = _json_document()
    document.pop(field_name)

    with pytest.raises(ValidationError, match="Field required"):
        ExecutionRecord.model_validate_json(json.dumps(document))


def test_extra_field_is_rejected() -> None:
    document = _json_document()
    document["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExecutionRecord.model_validate_json(json.dumps(document))


@pytest.mark.parametrize("version", ["", "0.9", "2.0", "1.0.0"])
def test_record_schema_version_must_match_exactly(version: str) -> None:
    document = _json_document()
    document["record_schema_version"] = version

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        ExecutionRecord.model_validate_json(json.dumps(document))


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("artifact_digest", "a" * 64),
        ("artifact_digest", f"sha256:{'A' * 64}"),
        ("configuration_digest", "sha256:short"),
        ("configuration_digest", f"sha1:{'b' * 64}"),
    ],
)
def test_digest_fields_reject_noncanonical_values(field_name: str, value: str) -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        _record(**{field_name: value})


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("base_commit_sha", "c" * 39),
        ("base_commit_sha", "C" * 40),
        ("candidate_commit_sha", "not-a-sha"),
        ("promotion_commit_sha", "d" * 64),
    ],
)
def test_git_sha_fields_require_full_lowercase_sha1(field_name: str, value: str) -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        _record(**{field_name: value})


@pytest.mark.parametrize(
    "execution_id",
    [
        "",
        ".",
        "..",
        "../escape",
        "folder/exec",
        r"folder\exec",
        "-leading",
        " leading-space",
        "trailing-space ",
        "trailing-dot.",
        "CON",
        "nul.json",
        "COM1",
        "a" * 129,
    ],
)
def test_execution_id_rejects_traversal_and_unsafe_path_components(execution_id: str) -> None:
    with pytest.raises(ValidationError):
        _record(execution_id=execution_id)


@pytest.mark.parametrize(
    "attempts",
    [
        {"node": -1},
        {"node": True},
        {"": 0},
        {"   ": 0},
    ],
)
def test_attempt_mapping_rejects_invalid_nodes_and_counts(attempts: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _record(attempt_by_node=attempts)


def test_revision_rejects_negative_and_boolean_values() -> None:
    with pytest.raises(ValidationError):
        _record(revision=-1)
    with pytest.raises(ValidationError):
        _record(revision=True)


def test_timestamps_require_utc_and_monotonic_order() -> None:
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        _record(created_at=_CREATED_AT.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="must use UTC"):
        _record(created_at=datetime(2026, 8, 6, 19, 30, tzinfo=timezone(-timedelta(hours=3))))
    with pytest.raises(ValidationError, match="cannot precede"):
        _record(updated_at=_CREATED_AT - timedelta(seconds=1))


def test_unknown_state_and_approval_status_are_rejected() -> None:
    document = _json_document()
    document["current_state"] = "UNKNOWN"
    with pytest.raises(ValidationError):
        ExecutionRecord.model_validate_json(json.dumps(document))

    document = _json_document()
    document["approval_status"] = "SKIPPED"
    with pytest.raises(ValidationError):
        ExecutionRecord.model_validate_json(json.dumps(document))


def test_failure_rejects_arbitrary_or_secret_payload_fields() -> None:
    document = _json_document()
    document["failure"] = {
        "code": "COMMAND_FAILED",
        "message": "redacted",
        "retryable": True,
        "node_id": "verify",
        "stderr": "SECRET=value",
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExecutionRecord.model_validate_json(json.dumps(document))


def test_execution_record_path_is_exact_and_path_safe(tmp_path: Path) -> None:
    expected = (
        tmp_path
        / ".harness"
        / "state"
        / "executions"
        / "exec-safe_1.0"
        / "execution.json"
    )
    assert execution_record_path(tmp_path, "exec-safe_1.0") == expected

    with pytest.raises(ValidationError):
        execution_record_path(tmp_path, "../escape")


def test_save_and_load_use_only_canonical_execution_json(tmp_path: Path) -> None:
    record = _record()
    destination = save_execution_record(tmp_path, record)

    assert destination == execution_record_path(tmp_path, record.execution_id)
    assert destination.read_text(encoding="utf-8") == record.canonical_json()
    assert load_execution_record(tmp_path, record.execution_id) == record
    assert not (destination.parent / "workflow-state.json").exists()
    assert not (destination.parent / "event-journal.jsonl").exists()
    assert not (destination.parent / "approval_request.json").exists()


def test_load_rejects_noncanonical_but_semantically_equal_json(tmp_path: Path) -> None:
    record = _record()
    destination = save_execution_record(tmp_path, record)
    destination.write_text(json.dumps(_json_document(record)), encoding="utf-8")

    with pytest.raises(ExecutionRecordIntegrityError, match="not canonical JSON"):
        load_execution_record(tmp_path, record.execution_id)


def test_load_rejects_crlf_bytes_as_noncanonical(tmp_path: Path) -> None:
    record = _record()
    destination = save_execution_record(tmp_path, record)
    destination.write_bytes(record.canonical_json().replace("\n", "\r\n").encode("utf-8"))

    with pytest.raises(ExecutionRecordIntegrityError, match="not canonical JSON"):
        load_execution_record(tmp_path, record.execution_id)


def test_load_rejects_record_bound_to_another_execution(tmp_path: Path) -> None:
    requested_id = "exec-requested"
    other = _record(execution_id="exec-other")
    destination = execution_record_path(tmp_path, requested_id)
    destination.parent.mkdir(parents=True)
    destination.write_text(other.canonical_json(), encoding="utf-8")

    with pytest.raises(ExecutionRecordIntegrityError, match="does not match"):
        load_execution_record(tmp_path, requested_id)


def test_load_rejects_invalid_utf8_and_missing_file(tmp_path: Path) -> None:
    execution_id = "exec-invalid"
    destination = execution_record_path(tmp_path, execution_id)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"\xff\xfe")

    with pytest.raises(ExecutionRecordIntegrityError, match="cannot read"):
        load_execution_record(tmp_path, execution_id)
    with pytest.raises(FileNotFoundError):
        load_execution_record(tmp_path, "exec-missing")


class _FailingStream:
    def __init__(self, stream: Any, stage: str):
        self._stream = stream
        self._stage = stage

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> object:
        return self._stream.__exit__(*args)

    def write(self, content: bytes) -> int:
        if self._stage == "write":
            raise OSError("controlled write failure")
        return self._stream.write(content)

    def flush(self) -> None:
        if self._stage == "flush":
            raise OSError("controlled flush failure")
        self._stream.flush()

    def fileno(self) -> int:
        return self._stream.fileno()


@pytest.mark.parametrize("stage", ["create", "write", "flush", "fsync", "replace"])
def test_atomic_failures_preserve_previous_bytes_and_remove_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    original = _record()
    destination = save_execution_record(tmp_path, original)
    previous = destination.read_bytes()
    changed = _record(revision=1, updated_at=_UPDATED_AT + timedelta(seconds=1))

    if stage == "create":
        monkeypatch.setattr(
            ATOMIC_FILE_MODULE.tempfile,
            "mkstemp",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                OSError("controlled create failure")
            ),
        )
    elif stage in {"write", "flush"}:
        original_fdopen = os.fdopen

        def failing_fdopen(*args: object, **kwargs: object) -> _FailingStream:
            return _FailingStream(original_fdopen(*args, **kwargs), stage)

        monkeypatch.setattr(ATOMIC_FILE_MODULE.os, "fdopen", failing_fdopen)
    elif stage == "fsync":
        monkeypatch.setattr(
            ATOMIC_FILE_MODULE.os,
            "fsync",
            lambda descriptor: (_ for _ in ()).throw(OSError("controlled fsync failure")),
        )
    else:
        monkeypatch.setattr(
            ATOMIC_FILE_MODULE.os,
            "replace",
            lambda source, target: (_ for _ in ()).throw(
                OSError("controlled replace failure")
            ),
        )

    with pytest.raises(ExecutionRecordWriteError, match=f"controlled {stage} failure"):
        save_execution_record(tmp_path, changed)

    assert destination.read_bytes() == previous
    assert not tuple(destination.parent.glob(".*.tmp"))


def test_public_contract_and_persistence_exports() -> None:
    from ai_engineering_harness import contracts, persistence

    assert contracts.ExecutionRecord is ExecutionRecord
    assert contracts.ExecutionState is ExecutionState
    assert contracts.ApprovalStatus is ApprovalStatus
    assert persistence.save_execution_record is save_execution_record
    assert persistence.load_execution_record is load_execution_record
