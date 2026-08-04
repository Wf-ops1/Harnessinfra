"""Compatibility tests for the legacy F1.3 policy validator adapter."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from compiler.validators.policy_validator import PolicyValidationError, PolicyValidator

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = ROOT / "src" / "ai_engineering_harness" / "defaults"


def _load_policy(reference: str) -> dict[str, Any]:
    document = yaml.safe_load((DEFAULTS / reference).read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _valid_legacy_graph() -> dict[str, Any]:
    return {
        "graph": {"name": "legacy-policy-fixture"},
        "policies": ["policies/tool_policy.yaml", "policies/verification_policy.yaml"],
        "nodes": [
            {
                "id": "analyze",
                "role": "requirement_analyst",
                "tool_permissions": [{"tool": "knowledge_retriever", "effect": "allow"}],
            },
            {
                "id": "verify",
                "executor": "deterministic_policy",
                "policy_ref": "policies/verification_policy.yaml",
            },
        ],
    }


def _validator_for(graph: dict[str, Any]) -> PolicyValidator:
    return PolicyValidator([_load_policy(reference) for reference in graph["policies"]])


def test_legacy_adapter_preserves_success_api_for_valid_graph() -> None:
    graph = _valid_legacy_graph()

    assert _validator_for(graph).validate(graph) is True


def test_legacy_adapter_rejects_missing_graph_name_and_invalid_policy_list() -> None:
    graph = _valid_legacy_graph()
    graph["graph"] = {}
    with pytest.raises(PolicyValidationError, match="graph.name"):
        _validator_for(_valid_legacy_graph()).validate(graph)

    graph = _valid_legacy_graph()
    graph["policies"] = "policies/tool_policy.yaml"
    with pytest.raises(PolicyValidationError, match="lista"):
        PolicyValidator([]).validate(graph)


def test_legacy_adapter_never_silently_skips_missing_policy_document() -> None:
    graph = _valid_legacy_graph()

    with pytest.raises(PolicyValidationError, match="Nem todas"):
        PolicyValidator([_load_policy("policies/tool_policy.yaml")]).validate(graph)


def test_legacy_adapter_rejects_unknown_policy_schema_key() -> None:
    graph = _valid_legacy_graph()
    policies = [_load_policy(reference) for reference in graph["policies"]]
    policies[0]["unknown_key"] = True

    with pytest.raises(PolicyValidationError, match="Extra inputs are not permitted"):
        PolicyValidator(policies).validate(graph)


def test_legacy_adapter_rejects_unknown_role_and_tool() -> None:
    graph = _valid_legacy_graph()
    graph["nodes"][0]["role"] = "missing_role"
    with pytest.raises(PolicyValidationError, match="missing_role"):
        _validator_for(graph).validate(graph)

    graph = _valid_legacy_graph()
    graph["nodes"][0]["tool_permissions"] = [{"tool": "missing_tool", "effect": "allow"}]
    with pytest.raises(PolicyValidationError, match="missing_tool"):
        _validator_for(graph).validate(graph)


def test_legacy_adapter_rejects_unauthorized_tool_and_policy_ref_outside_graph() -> None:
    graph = _valid_legacy_graph()
    graph["nodes"][0]["tool_permissions"] = [{"tool": "test_runner", "effect": "allow"}]
    with pytest.raises(PolicyValidationError, match="not authorized"):
        _validator_for(graph).validate(graph)

    graph = _valid_legacy_graph()
    graph["policies"] = ["policies/tool_policy.yaml"]
    with pytest.raises(PolicyValidationError, match="not declared"):
        _validator_for(graph).validate(graph)


def test_legacy_adapter_rejects_conflicting_permissions_without_mutating_input() -> None:
    graph = _valid_legacy_graph()
    graph["nodes"][0]["tool_permissions"] = [
        {"tool": "knowledge_retriever", "effect": "allow"},
        {"tool": "knowledge_retriever", "effect": "deny"},
    ]
    before = deepcopy(graph)

    with pytest.raises(PolicyValidationError, match="repeats or conflicts"):
        _validator_for(graph).validate(graph)
    assert graph == before
