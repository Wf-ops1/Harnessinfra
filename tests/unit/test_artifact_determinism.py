"""Defensibility proofs for the deterministic F1.5 compiled artifact."""

from __future__ import annotations

import importlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Self

import pytest
import yaml

from ai_engineering_harness.compiler import GraphCompiler, GraphWriteError
from ai_engineering_harness.contracts import CompiledGraphArtifact
from ai_engineering_harness.runtime.maf_adapter import (
    ArtifactCompatibilityError,
    ArtifactIntegrityError,
    MAFAdapter,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPHS = ROOT / "src" / "ai_engineering_harness" / "defaults" / "graphs"
COMPILER_MODULE = importlib.import_module("ai_engineering_harness.compiler.compiler")


def _deterministic_graph(name: str = "deterministic") -> dict[str, Any]:
    return {
        "graph": {
            "name": name,
            "graph_schema_version": "1.0",
            "definition_version": "1.0.0",
            "entrypoint": "prepare",
            "status": "stable",
        },
        "nodes": [
            {
                "id": "prepare",
                "type": "deterministic",
                "executor": "deterministic_gate",
                "gate_name": "prepared",
                "on_success": "verify",
                "on_failure": "failed",
            },
            {
                "id": "verify",
                "type": "deterministic",
                "executor": "deterministic_gate",
                "gate_name": "verified",
                "on_success": "completed",
                "on_failure": "failed",
            },
        ],
        "terminal_states": [
            {"id": "completed", "outcome": "success"},
            {"id": "failed", "outcome": "failure"},
        ],
        "policies": [],
        "contracts": [],
    }


def _capability_graph() -> dict[str, Any]:
    contract = "contracts/nodes/context_sufficiency.py#RetrievalRequest"
    return {
        "graph": {
            "name": "capabilities",
            "graph_schema_version": "1.0",
            "definition_version": "1.0.0",
            "entrypoint": "analyze",
            "status": "stable",
        },
        "nodes": [
            {
                "id": "analyze",
                "type": "agent",
                "role": "requirement_analyst",
                "input_contract": contract,
                "output_contract": contract,
                "tool_permissions": [
                    {"tool": "file_reader", "effect": "deny"},
                    {"tool": "knowledge_retriever", "effect": "allow"},
                ],
                "on_success": "implement",
                "on_failure": "failed",
            },
            {
                "id": "implement",
                "type": "agent",
                "role": "code_agent",
                "input_contract": contract,
                "output_contract": contract,
                "tool_permissions": [{"tool": "file_writer", "effect": "allow"}],
                "on_success": "completed",
                "on_failure": "failed",
            },
        ],
        "terminal_states": [
            {"id": "completed", "outcome": "success"},
            {"id": "failed", "outcome": "failure"},
        ],
        "policies": ["policies/tool_policy.yaml"],
        "contracts": [],
    }


def _write_graph(project_root: Path, document: dict[str, Any], name: str = "graph.yaml") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    source = project_root / name
    source.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return source


def _compile(project_root: Path, document: dict[str, Any]) -> Path:
    source = _write_graph(project_root, document)
    return GraphCompiler(project_root).compile_graph(source)


def _compile_default(project_root: Path, graph_name: str = "new-feature") -> Path:
    source = project_root / f"{graph_name}.yaml"
    project_root.mkdir(parents=True, exist_ok=True)
    source.write_bytes((DEFAULT_GRAPHS / f"{graph_name}.yaml").read_bytes())
    return GraphCompiler(project_root).compile_graph(source, graph_name)


def _rewrite_canonical(path: Path, document: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_identical_sources_emit_exact_bytes_and_complete_portable_manifest(tmp_path: Path) -> None:
    output = _compile(tmp_path, _deterministic_graph())
    first = output.read_bytes()
    second_output = GraphCompiler(tmp_path).compile_graph(tmp_path / "graph.yaml")

    assert second_output.read_bytes() == first
    artifact = MAFAdapter.load_and_validate(output)
    assert artifact.artifact_schema_version == "2.0"
    assert len(artifact.source_manifest) == 24
    assert {source.source_kind for source in artifact.source_manifest} == {
        "graph",
        "policy",
        "role",
        "role_prompt",
        "tool_registry",
    }
    assert all(
        source.source_id.startswith(("project://", "package://"))
        for source in artifact.source_manifest
    )
    serialized = first.decode("utf-8")
    assert str(tmp_path.resolve()) not in serialized
    assert "compiled_at" not in serialized
    assert "timestamp" not in serialized
    assert serialized.endswith("\n")


def test_semantic_reordering_preserves_semantic_digests_only(tmp_path: Path) -> None:
    left_document = _deterministic_graph("ordered")
    right_document = _deterministic_graph("ordered")
    right_document["nodes"].reverse()
    right_document["terminal_states"].reverse()

    left = _compile(tmp_path / "left", left_document)
    right = _compile(tmp_path / "right", right_document)
    left_artifact = CompiledGraphArtifact.model_validate_json(left.read_text(encoding="utf-8"))
    right_artifact = CompiledGraphArtifact.model_validate_json(right.read_text(encoding="utf-8"))

    assert left_artifact.graph == right_artifact.graph
    assert left_artifact.graph_digest == right_artifact.graph_digest
    assert left_artifact.policy_digest == right_artifact.policy_digest
    assert left_artifact.contract_digests == right_artifact.contract_digests
    assert left_artifact.source_manifest != right_artifact.source_manifest


def _mutate_graph(document: dict[str, Any]) -> None:
    document["graph"]["graph"]["definition_version"] = "tampered"


def _mutate_policy(document: dict[str, Any]) -> None:
    document["resolved_policies"][0]["definition_version"] = "tampered"


def _mutate_effective_policy_shape(document: dict[str, Any]) -> None:
    tool_policy = next(
        policy
        for policy in document["resolved_policies"]
        if policy["requested_reference"] == "policies/tool_policy.yaml"
    )
    first_role = next(iter(tool_policy["effective_policy"]["roles"].values()))
    first_role["nodes"] = [{"broken": True}]


def _mutate_contract_schema(document: dict[str, Any]) -> None:
    document["resolved_contracts"][0]["contract_schema"]["tampered"] = True


def _mutate_contract_index(document: dict[str, Any]) -> None:
    document["contract_digests"][0]["digest"] = "sha256:" + "0" * 64


def _mutate_manifest_digest(document: dict[str, Any]) -> None:
    document["source_manifest"][0]["content_digest"] = "sha256:" + "0" * 64


def _mutate_capabilities(document: dict[str, Any]) -> None:
    document["required_capabilities"].append("unbound_capability")


@pytest.mark.parametrize(
    "mutation",
    [
        _mutate_graph,
        _mutate_policy,
        _mutate_effective_policy_shape,
        _mutate_contract_schema,
        _mutate_contract_index,
        _mutate_manifest_digest,
        _mutate_capabilities,
    ],
)
def test_every_integrity_view_is_recomputed_before_return(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    output = _compile_default(tmp_path)
    document = json.loads(output.read_text(encoding="utf-8"))
    mutation(document)
    _rewrite_canonical(output, document)

    with pytest.raises(ArtifactIntegrityError):
        MAFAdapter.load_and_validate(output)


@pytest.mark.parametrize(
    ("location", "value"),
    [
        (("artifact_schema_version",), "1.0"),
        (("artifact_schema_version",), "999.0"),
        (("package_version",), "999.0.0"),
        (("graph", "graph", "graph_schema_version"), "999.0"),
        (("resolved_policies", 0, "policy_schema_version"), "999.0"),
    ],
)
def test_every_version_namespace_requires_an_exact_match(
    tmp_path: Path,
    location: tuple[str | int, ...],
    value: str,
) -> None:
    output = _compile_default(tmp_path)
    document = json.loads(output.read_text(encoding="utf-8"))
    target: Any = document
    for part in location[:-1]:
        target = target[part]
    target[location[-1]] = value
    _rewrite_canonical(output, document)

    with pytest.raises(ArtifactCompatibilityError):
        MAFAdapter.load_and_validate(output)


@pytest.mark.parametrize(
    "invalid_source_id",
    [
        "project://C:/secret.yaml",
        "project://../secret.yaml",
        "project://folder\\secret.yaml",
        "package://different.package/policy.yaml",
    ],
)
def test_nonportable_manifest_source_ids_fail_closed(
    tmp_path: Path,
    invalid_source_id: str,
) -> None:
    output = _compile(tmp_path, _deterministic_graph())
    document = json.loads(output.read_text(encoding="utf-8"))
    document["source_manifest"][0]["source_id"] = invalid_source_id
    _rewrite_canonical(output, document)

    with pytest.raises(ArtifactIntegrityError):
        MAFAdapter.load_and_validate(output)


def test_missing_incomplete_duplicate_and_extra_manifest_sources_fail_closed(
    tmp_path: Path,
) -> None:
    output = _compile(tmp_path, _deterministic_graph())
    original = json.loads(output.read_text(encoding="utf-8"))

    missing = json.loads(json.dumps(original))
    missing["source_manifest"][0]["source_id"] = "project://missing.yaml"
    _rewrite_canonical(output, missing)
    with pytest.raises(ArtifactIntegrityError):
        MAFAdapter.load_and_validate(output)

    incomplete = json.loads(json.dumps(original))
    incomplete["source_manifest"] = [
        source
        for source in incomplete["source_manifest"]
        if not (
            source["source_kind"] == "policy"
            and source["source_id"].endswith("verification_policy.yaml")
        )
    ]
    _rewrite_canonical(output, incomplete)
    with pytest.raises(ArtifactIntegrityError, match="does not exactly match"):
        MAFAdapter.load_and_validate(output)

    duplicate = json.loads(json.dumps(original))
    duplicate["source_manifest"].append(duplicate["source_manifest"][-1])
    _rewrite_canonical(output, duplicate)
    with pytest.raises(ArtifactIntegrityError):
        MAFAdapter.load_and_validate(output)

    extra = json.loads(json.dumps(original))
    extra_source = dict(extra["source_manifest"][0])
    extra_source["source_kind"] = "policy"
    extra["source_manifest"].append(extra_source)
    extra["source_manifest"].sort(
        key=lambda source: (source["source_kind"], source["source_id"])
    )
    _rewrite_canonical(output, extra)
    with pytest.raises(ArtifactIntegrityError, match="does not exactly match"):
        MAFAdapter.load_and_validate(output)


def test_external_json_schema_is_manifested_and_revalidated(tmp_path: Path) -> None:
    schema_path = tmp_path / ".harness" / "contracts" / "payload.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    graph = _deterministic_graph("external-contract")
    graph["contracts"] = ["jsonschema:payload.json"]

    output = _compile(tmp_path, graph)
    artifact = MAFAdapter.load_and_validate(output)
    schema_sources = [
        source
        for source in artifact.source_manifest
        if source.source_kind == "contract_schema"
    ]
    assert len(schema_sources) == 1
    assert schema_sources[0].source_id == "project://.harness/contracts/payload.json"

    schema_path.write_text(
        schema_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ArtifactIntegrityError, match="digest mismatch"):
        MAFAdapter.load_and_validate(output)


def test_required_capabilities_are_only_effective_sorted_allows(tmp_path: Path) -> None:
    output = _compile(tmp_path, _capability_graph())
    artifact = MAFAdapter.load_and_validate(output)

    assert artifact.required_capabilities == ("file_writer", "knowledge_retriever")
    assert "file_reader" not in artifact.required_capabilities
    assert "test_runner" not in artifact.required_capabilities


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
    source = _write_graph(tmp_path, _deterministic_graph())
    compiler = GraphCompiler(tmp_path)
    output = compiler.compile_graph(source)
    previous = output.read_bytes()
    changed = _deterministic_graph()
    changed["graph"]["definition_version"] = "2.0.0"
    source.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")

    if stage == "create":
        monkeypatch.setattr(
            COMPILER_MODULE.tempfile,
            "mkstemp",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("controlled create failure")),
        )
    elif stage in {"write", "flush"}:
        original_fdopen = os.fdopen

        def failing_fdopen(*args: object, **kwargs: object) -> _FailingStream:
            return _FailingStream(original_fdopen(*args, **kwargs), stage)

        monkeypatch.setattr(COMPILER_MODULE.os, "fdopen", failing_fdopen)
    elif stage == "fsync":
        monkeypatch.setattr(
            COMPILER_MODULE.os,
            "fsync",
            lambda descriptor: (_ for _ in ()).throw(OSError("controlled fsync failure")),
        )
    else:
        monkeypatch.setattr(
            COMPILER_MODULE.os,
            "replace",
            lambda source_path, target_path: (_ for _ in ()).throw(
                OSError("controlled replace failure")
            ),
        )

    with pytest.raises(GraphWriteError, match=f"controlled {stage} failure"):
        compiler.compile_graph(source)

    assert output.read_bytes() == previous
    assert not tuple(compiler.output_dir.glob("*.tmp"))


def test_noncanonical_but_semantically_equal_json_is_rejected(tmp_path: Path) -> None:
    output = _compile(tmp_path, _deterministic_graph())
    document = json.loads(output.read_text(encoding="utf-8"))
    output.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="not canonical JSON"):
        MAFAdapter.load_and_validate(output)
