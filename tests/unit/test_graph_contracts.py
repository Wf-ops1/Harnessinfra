"""Tests for the strict F1.1 graph and compiled-artifact contracts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

import ai_engineering_harness.contracts as public_contracts
from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    CompiledGraphArtifact,
    DeterministicNodeSpec,
    GraphMetadata,
    GraphSpec,
    HumanApprovalNodeSpec,
    NodeSpec,
    RetryPolicySpec,
    TerminalStateSpec,
    ToolPermissionSpec,
)
from ai_engineering_harness.versioning import (
    ARTIFACT_SCHEMA_VERSION,
    GRAPH_SCHEMA_VERSION,
    PACKAGE_VERSION,
)

PUBLIC_GRAPH_SYMBOLS = {
    "GraphSpec",
    "GraphMetadata",
    "NodeSpec",
    "AgentNodeSpec",
    "DeterministicNodeSpec",
    "HumanApprovalNodeSpec",
    "TerminalStateSpec",
    "RetryPolicySpec",
    "ToolPermissionSpec",
    "CompiledGraphArtifact",
}


def _valid_graph_data() -> dict[str, Any]:
    return {
        "graph": {
            "name": "new-feature",
            "graph_schema_version": GRAPH_SCHEMA_VERSION,
            "definition_version": "3.2.0",
            "entrypoint": "context_retrieval",
            "status": "stable",
            "description": "Typed graph contract fixture",
        },
        "policies": ["policies/verification_policy.yaml"],
        "contracts": ["RetrievalRequest", "ContextSufficiencyReport"],
        "nodes": [
            {
                "id": "context_retrieval",
                "type": "agent",
                "role": "requirement_analyst",
                "input_contract": "RetrievalRequest",
                "output_contract": "ContextSufficiencyReport",
                "tool_permissions": [{"tool": "knowledge_retriever", "effect": "allow"}],
                "on_success": "verification_gate",
                "on_failure": "failed",
            },
            {
                "id": "verification_gate",
                "type": "deterministic",
                "executor": "deterministic_policy",
                "policy_ref": "policies/verification_policy.yaml",
                "on_success": "approval",
                "on_failure": "failed",
            },
            {
                "id": "approval",
                "type": "human_approval",
                "approval_strategy": "explicit",
                "on_success": "completed",
                "on_failure": "failed",
            },
        ],
        "terminal_states": [
            {"id": "completed", "outcome": "success"},
            {"id": "failed", "outcome": "failure"},
        ],
    }


def _cyclic_graph_data() -> dict[str, Any]:
    data = _valid_graph_data()
    data["nodes"] = [
        {
            "id": "context_retrieval",
            "type": "agent",
            "role": "requirement_analyst",
            "input_contract": "RetrievalRequest",
            "output_contract": "ContextSufficiencyReport",
            "on_success": "verification_gate",
            "on_failure": "failed",
        },
        {
            "id": "verification_gate",
            "type": "deterministic",
            "executor": "deterministic_gate",
            "gate_name": "context_is_sufficient",
            "on_success": "context_retrieval",
            "on_failure": "completed",
        },
    ]
    return data


def test_public_graph_contract_api_exports_all_required_symbols() -> None:
    assert PUBLIC_GRAPH_SYMBOLS <= set(public_contracts.__all__)
    for symbol in PUBLIC_GRAPH_SYMBOLS:
        assert getattr(public_contracts, symbol) is not None


def test_valid_graph_uses_discriminated_node_models() -> None:
    graph = GraphSpec.model_validate(_valid_graph_data())

    assert isinstance(graph.graph, GraphMetadata)
    assert isinstance(graph.nodes, tuple)
    assert isinstance(graph.terminal_states, tuple)
    assert isinstance(graph.policies, tuple)
    assert isinstance(graph.contracts, tuple)
    assert isinstance(graph.nodes[0], AgentNodeSpec)
    assert isinstance(graph.nodes[1], DeterministicNodeSpec)
    assert isinstance(graph.nodes[2], HumanApprovalNodeSpec)
    assert isinstance(graph.terminal_states[0], TerminalStateSpec)
    assert isinstance(graph.nodes[0].tool_permissions[0], ToolPermissionSpec)

    parsed_node = TypeAdapter(NodeSpec).validate_python(_valid_graph_data()["nodes"][0])
    assert isinstance(parsed_node, AgentNodeSpec)


def test_validated_graph_cannot_be_mutated() -> None:
    graph = GraphSpec.model_validate(_valid_graph_data())

    with pytest.raises(ValidationError, match="frozen"):
        graph.graph.entrypoint = "approval"

    with pytest.raises(AttributeError):
        graph.nodes.append(graph.nodes[0])  # type: ignore[attr-defined]


def test_schema_version_alias_serializes_to_canonical_namespace() -> None:
    data = _valid_graph_data()
    data["graph"]["schema_version"] = data["graph"].pop("graph_schema_version")

    dumped = GraphSpec.model_validate(data).model_dump(mode="json")

    assert dumped["graph"]["graph_schema_version"] == GRAPH_SCHEMA_VERSION
    assert "schema_version" not in dumped["graph"]


def test_compiled_artifact_round_trip() -> None:
    artifact = CompiledGraphArtifact(
        artifact_schema_version=ARTIFACT_SCHEMA_VERSION,
        package_version=PACKAGE_VERSION,
        graph=GraphSpec.model_validate(_valid_graph_data()),
    )

    restored = CompiledGraphArtifact.model_validate_json(artifact.model_dump_json())

    assert restored == artifact
    assert restored.graph.graph.graph_schema_version == GRAPH_SCHEMA_VERSION
    assert restored.resolved_contracts == ()
    assert restored.resolved_policies == ()


def test_duplicate_id_is_rejected_across_nodes_and_terminals() -> None:
    data = _valid_graph_data()
    data["terminal_states"][0]["id"] = "context_retrieval"

    with pytest.raises(ValidationError, match="IDs must be unique"):
        GraphSpec.model_validate(data)


def test_missing_entrypoint_is_rejected() -> None:
    data = _valid_graph_data()
    del data["graph"]["entrypoint"]

    with pytest.raises(ValidationError, match="entrypoint"):
        GraphSpec.model_validate(data)


def test_unknown_entrypoint_is_rejected() -> None:
    data = _valid_graph_data()
    data["graph"]["entrypoint"] = "missing_node"

    with pytest.raises(ValidationError, match="entrypoint"):
        GraphSpec.model_validate(data)


@pytest.mark.parametrize("outcome", ["success", "failure"])
def test_both_terminal_outcomes_are_required(outcome: str) -> None:
    data = _valid_graph_data()
    for terminal in data["terminal_states"]:
        terminal["outcome"] = outcome

    with pytest.raises(ValidationError, match="terminal states must include outcomes"):
        GraphSpec.model_validate(data)


def test_broken_edge_is_rejected() -> None:
    data = _valid_graph_data()
    data["nodes"][0]["on_success"] = "missing_target"

    with pytest.raises(ValidationError, match="unknown targets"):
        GraphSpec.model_validate(data)


def test_unreachable_node_is_rejected() -> None:
    data = _valid_graph_data()
    data["nodes"].append(
        {
            "id": "orphan",
            "type": "human_approval",
            "approval_strategy": "explicit",
            "on_success": "completed",
            "on_failure": "failed",
        }
    )

    with pytest.raises(ValidationError, match="unreachable"):
        GraphSpec.model_validate(data)


def test_implicit_edge_is_rejected() -> None:
    data = _valid_graph_data()
    del data["nodes"][0]["on_failure"]

    with pytest.raises(ValidationError, match="on_failure"):
        GraphSpec.model_validate(data)


def test_every_node_in_cycle_requires_retry_policy() -> None:
    data = _cyclic_graph_data()
    data["nodes"][0]["retry_policy"] = {
        "max_iterations": 3,
        "exit_condition": "context_is_sufficient",
    }

    with pytest.raises(ValidationError, match="verification_gate"):
        GraphSpec.model_validate(data)


def test_explicitly_governed_cycle_is_accepted() -> None:
    data = _cyclic_graph_data()
    for node in data["nodes"]:
        node["retry_policy"] = {
            "max_iterations": 3,
            "exit_condition": "context_is_sufficient",
        }

    graph = GraphSpec.model_validate(data)

    assert all(node.retry_policy is not None for node in graph.nodes)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_iterations", 0),
        ("exit_condition", ""),
        ("exit_condition", "   "),
    ],
)
def test_invalid_retry_policy_is_rejected(field: str, value: object) -> None:
    data: dict[str, object] = {"max_iterations": 3, "exit_condition": "done"}
    data[field] = value

    with pytest.raises(ValidationError):
        RetryPolicySpec.model_validate(data)


def test_deterministic_executor_requires_matching_field() -> None:
    data = _valid_graph_data()["nodes"][1]
    data["executor"] = "deterministic_command"

    with pytest.raises(ValidationError, match="requires 'command'"):
        DeterministicNodeSpec.model_validate(data)


@pytest.mark.parametrize(
    ("node_index", "extra_field", "value"),
    [
        (0, "command", "pytest"),
        (1, "role", "code_agent"),
        (2, "executor", "deterministic_gate"),
    ],
)
def test_node_type_rejects_incompatible_fields(node_index: int, extra_field: str, value: str) -> None:
    node = deepcopy(_valid_graph_data()["nodes"][node_index])
    node[extra_field] = value

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TypeAdapter(NodeSpec).validate_python(node)


def test_unknown_graph_field_is_rejected() -> None:
    data = _valid_graph_data()
    data["implicit_next"] = "completed"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        GraphSpec.model_validate(data)


def test_strict_mode_rejects_version_coercion() -> None:
    data = _valid_graph_data()
    data["graph"]["graph_schema_version"] = 1

    with pytest.raises(ValidationError):
        GraphSpec.model_validate(data)


def test_tool_permission_effect_is_closed() -> None:
    with pytest.raises(ValidationError):
        ToolPermissionSpec(tool="terminal", effect="prompt")  # type: ignore[arg-type]
