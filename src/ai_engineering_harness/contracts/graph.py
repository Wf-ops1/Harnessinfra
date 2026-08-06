"""Strict, immutable contracts for graph specifications and compiled artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal, Self, TypeAlias, cast

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ai_engineering_harness.versioning import (
    ARTIFACT_SCHEMA_VERSION,
    GRAPH_SCHEMA_VERSION,
    PACKAGE_VERSION,
    POLICY_SCHEMA_VERSION,
)

from .policies import ResolvedPolicySpec
from .registry import ResolvedContractSpec

_NonEmptyStr: TypeAlias = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOOL_POLICY_REFERENCE = "policies/tool_policy.yaml"


class _StrictFrozenModel(BaseModel):
    """Shared fail-closed configuration for serialized graph contracts."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class RetryPolicySpec(_StrictFrozenModel):
    """Explicit bound and exit condition required for a graph cycle."""

    max_iterations: int = Field(gt=0)
    exit_condition: _NonEmptyStr


class ToolPermissionSpec(_StrictFrozenModel):
    """A tool permission requested by an agent node."""

    tool: _NonEmptyStr
    effect: Literal["allow", "deny"]


class _BaseNodeSpec(_StrictFrozenModel):
    """Fields shared by every executable node variant."""

    id: _NonEmptyStr
    on_success: _NonEmptyStr
    on_failure: _NonEmptyStr
    retry_policy: RetryPolicySpec | None = None


class AgentNodeSpec(_BaseNodeSpec):
    """A node executed by an agent role with typed input and output contracts."""

    type: Literal["agent"]
    role: _NonEmptyStr
    input_contract: _NonEmptyStr
    output_contract: _NonEmptyStr
    tool_permissions: tuple[ToolPermissionSpec, ...] = ()

    @field_validator("tool_permissions", mode="before")
    @classmethod
    def freeze_tool_permissions(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class DeterministicNodeSpec(_BaseNodeSpec):
    """A deterministic policy, gate, or command node."""

    type: Literal["deterministic"]
    executor: Literal["deterministic_policy", "deterministic_gate", "deterministic_command"]
    policy_ref: _NonEmptyStr | None = None
    gate_name: _NonEmptyStr | None = None
    command: _NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_executor_fields(self) -> Self:
        required_field = {
            "deterministic_policy": "policy_ref",
            "deterministic_gate": "gate_name",
            "deterministic_command": "command",
        }[self.executor]
        executor_fields = {
            "policy_ref": self.policy_ref,
            "gate_name": self.gate_name,
            "command": self.command,
        }

        if executor_fields[required_field] is None:
            raise ValueError(f"executor {self.executor!r} requires {required_field!r}")

        incompatible = sorted(
            field_name
            for field_name, value in executor_fields.items()
            if field_name != required_field and value is not None
        )
        if incompatible:
            raise ValueError(
                f"executor {self.executor!r} is incompatible with fields: {', '.join(incompatible)}"
            )
        return self


class HumanApprovalNodeSpec(_BaseNodeSpec):
    """A node that requires an explicit human approval strategy."""

    type: Literal["human_approval"]
    approval_strategy: _NonEmptyStr


NodeSpec: TypeAlias = Annotated[
    AgentNodeSpec | DeterministicNodeSpec | HumanApprovalNodeSpec,
    Field(discriminator="type"),
]


class GraphMetadata(_StrictFrozenModel):
    """Identity, schema namespace, and entrypoint for a graph definition."""

    name: _NonEmptyStr
    graph_schema_version: _NonEmptyStr = Field(
        validation_alias=AliasChoices("graph_schema_version", "schema_version")
    )
    definition_version: _NonEmptyStr
    entrypoint: _NonEmptyStr
    status: _NonEmptyStr
    description: _NonEmptyStr | None = None


class TerminalStateSpec(_StrictFrozenModel):
    """An explicit terminal state and its final outcome."""

    id: _NonEmptyStr
    outcome: Literal["success", "failure"]


class GraphSpec(_StrictFrozenModel):
    """A fully explicit and topologically valid executable graph."""

    graph: GraphMetadata
    nodes: tuple[NodeSpec, ...] = Field(min_length=1)
    terminal_states: tuple[TerminalStateSpec, ...] = Field(min_length=2)
    policies: tuple[_NonEmptyStr, ...] = ()
    contracts: tuple[_NonEmptyStr, ...] = ()

    @field_validator("nodes", "terminal_states", "policies", "contracts", mode="before")
    @classmethod
    def freeze_sequences(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_topology(self) -> Self:
        nodes_by_id = {node.id: node for node in self.nodes}
        terminal_ids = {terminal.id for terminal in self.terminal_states}
        all_ids = [node.id for node in self.nodes] + [terminal.id for terminal in self.terminal_states]
        duplicate_ids = sorted(identifier for identifier, count in Counter(all_ids).items() if count > 1)
        if duplicate_ids:
            raise ValueError(f"graph IDs must be unique; duplicates: {', '.join(duplicate_ids)}")

        if self.graph.entrypoint not in nodes_by_id:
            raise ValueError(f"entrypoint {self.graph.entrypoint!r} does not reference an existing node")

        outcomes = {terminal.outcome for terminal in self.terminal_states}
        missing_outcomes = sorted({"success", "failure"} - outcomes)
        if missing_outcomes:
            raise ValueError(f"terminal states must include outcomes: {', '.join(missing_outcomes)}")

        valid_targets = set(nodes_by_id) | terminal_ids
        broken_edges = sorted(
            f"{node.id}.{edge_name}->{target}"
            for node in self.nodes
            for edge_name, target in (("on_success", node.on_success), ("on_failure", node.on_failure))
            if target not in valid_targets
        )
        if broken_edges:
            raise ValueError(f"edges reference unknown targets: {', '.join(broken_edges)}")

        adjacency = {
            node.id: {target for target in (node.on_success, node.on_failure) if target in nodes_by_id}
            for node in self.nodes
        }
        reachable = self._reachable_nodes(self.graph.entrypoint, adjacency)
        unreachable = sorted(set(nodes_by_id) - reachable)
        if unreachable:
            raise ValueError(f"nodes are unreachable from entrypoint: {', '.join(unreachable)}")

        cyclic_nodes = {
            node_id
            for node_id, targets in adjacency.items()
            if node_id in targets or any(self._can_reach(target, node_id, adjacency) for target in targets)
        }
        ungoverned_cycles = sorted(
            node_id for node_id in cyclic_nodes if nodes_by_id[node_id].retry_policy is None
        )
        if ungoverned_cycles:
            raise ValueError(
                "every node participating in a cycle requires retry_policy; missing: "
                + ", ".join(ungoverned_cycles)
            )
        return self

    @staticmethod
    def _reachable_nodes(start: str, adjacency: dict[str, set[str]]) -> set[str]:
        reachable: set[str] = set()
        pending = [start]
        while pending:
            node_id = pending.pop()
            if node_id in reachable:
                continue
            reachable.add(node_id)
            pending.extend(adjacency[node_id] - reachable)
        return reachable

    @staticmethod
    def _can_reach(start: str, destination: str, adjacency: dict[str, set[str]]) -> bool:
        visited: set[str] = set()
        pending = [start]
        while pending:
            node_id = pending.pop()
            if node_id == destination:
                return True
            if node_id in visited:
                continue
            visited.add(node_id)
            pending.extend(adjacency[node_id] - visited)
        return False


class ContractDigestSpec(_StrictFrozenModel):
    """Stable digest index entry for one resolved contract reference."""

    requested_reference: _NonEmptyStr
    canonical_name: _NonEmptyStr
    digest: str = Field(pattern=_DIGEST_PATTERN.pattern)


class SourceManifestEntry(_StrictFrozenModel):
    """Portable identity and content digest for one compilation input file."""

    source_kind: Literal[
        "graph",
        "contract_schema",
        "policy",
        "role",
        "role_prompt",
        "tool_registry",
    ]
    source_id: _NonEmptyStr
    content_digest: str = Field(pattern=_DIGEST_PATTERN.pattern)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        project_prefix = "project://"
        package_prefix = "package://"
        if value.startswith(project_prefix):
            relative = value.removeprefix(project_prefix)
        elif value.startswith(package_prefix):
            relative = value.removeprefix(package_prefix)
            if not relative.startswith("ai_engineering_harness.defaults/"):
                raise ValueError(
                    "package source IDs must begin with "
                    "package://ai_engineering_harness.defaults/"
                )
        else:
            raise ValueError("source_id must use project:// or package://")

        if not relative or "\\" in relative or ":" in relative:
            raise ValueError("source_id must contain a normalized POSIX relative path")
        parts = relative.split("/")
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("source_id cannot be absolute or contain traversal")
        if path.as_posix() != relative:
            raise ValueError("source_id must be canonically normalized")
        return value


def _canonical_json_bytes(value: object) -> bytes:
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"artifact content is not canonical JSON: {exc}") from exc
    return serialized.encode("utf-8")


def _semantic_digest(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json_bytes(value)).hexdigest()}"


def _canonicalize_graph(graph: GraphSpec) -> GraphSpec:
    data = graph.model_dump(mode="json")
    nodes = cast(list[dict[str, Any]], data["nodes"])
    for node in nodes:
        permissions = node.get("tool_permissions")
        if isinstance(permissions, list):
            permissions.sort(key=lambda item: (item["tool"], item["effect"]))
    nodes.sort(key=lambda node: cast(str, node["id"]))

    terminal_states = cast(list[dict[str, Any]], data["terminal_states"])
    terminal_states.sort(key=lambda terminal: cast(str, terminal["id"]))
    data["policies"] = sorted(cast(list[str], data["policies"]))
    data["contracts"] = sorted(cast(list[str], data["contracts"]))
    return GraphSpec.model_validate(data)


def _canonicalize_contracts(
    contracts: tuple[ResolvedContractSpec, ...],
) -> tuple[ResolvedContractSpec, ...]:
    return tuple(
        sorted(
            contracts,
            key=lambda contract: (contract.requested_reference, contract.canonical_name),
        )
    )


def _canonicalize_policies(
    policies: tuple[ResolvedPolicySpec, ...],
) -> tuple[ResolvedPolicySpec, ...]:
    canonical: list[ResolvedPolicySpec] = []
    for policy in policies:
        data = policy.model_dump(mode="json")
        if policy.requested_reference == _TOOL_POLICY_REFERENCE:
            effective_policy = cast(dict[str, Any], data["effective_policy"])
            roles = effective_policy.get("roles")
            if isinstance(roles, dict):
                for role in roles.values():
                    if isinstance(role, dict) and isinstance(role.get("nodes"), list):
                        nodes = cast(list[object], role["nodes"])
                        if not all(
                            isinstance(node, dict)
                            and isinstance(node.get("node_id"), str)
                            and bool(node["node_id"].strip())
                            for node in nodes
                        ):
                            raise ValueError(
                                "resolved tool policy nodes must contain node_id strings"
                            )
                        cast(list[dict[str, Any]], nodes).sort(
                            key=lambda node: cast(str, node["node_id"])
                        )
        canonical.append(ResolvedPolicySpec.model_validate(data))
    return tuple(sorted(canonical, key=lambda policy: policy.requested_reference))


def _contract_digest_index(
    contracts: tuple[ResolvedContractSpec, ...],
) -> tuple[ContractDigestSpec, ...]:
    return tuple(
        ContractDigestSpec(
            requested_reference=contract.requested_reference,
            canonical_name=contract.canonical_name,
            digest=contract.digest,
        )
        for contract in _canonicalize_contracts(contracts)
    )


def _required_capabilities(policies: tuple[ResolvedPolicySpec, ...]) -> tuple[str, ...]:
    capabilities: set[str] = set()
    tool_policies = [
        policy for policy in policies if policy.requested_reference == _TOOL_POLICY_REFERENCE
    ]
    if len(tool_policies) > 1:
        raise ValueError("resolved tool policy reference must be unique")
    if not tool_policies:
        return ()

    roles = tool_policies[0].effective_policy.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("resolved tool policy must contain a roles object")  # noqa: TRY004
    for role in roles.values():
        if not isinstance(role, dict) or not isinstance(role.get("nodes"), list):
            raise ValueError(  # noqa: TRY004
                "resolved tool policy roles must contain node lists"
            )
        for node in role["nodes"]:
            if not isinstance(node, dict) or not isinstance(node.get("allowed_tools"), list):
                raise ValueError(  # noqa: TRY004
                    "resolved tool policy nodes must contain allowed_tools lists"
                )
            for capability in node["allowed_tools"]:
                if not isinstance(capability, str) or not capability.strip():
                    raise ValueError("required capabilities must be non-empty strings")
                capabilities.add(capability)
    return tuple(sorted(capabilities))


class CompiledGraphArtifact(_StrictFrozenModel):
    """Canonical, self-consistent artifact envelope consumed by the runtime loader."""

    artifact_schema_version: _NonEmptyStr
    package_version: _NonEmptyStr
    graph_digest: str = Field(pattern=_DIGEST_PATTERN.pattern)
    policy_digest: str = Field(pattern=_DIGEST_PATTERN.pattern)
    contract_digests: tuple[ContractDigestSpec, ...]
    source_manifest: tuple[SourceManifestEntry, ...] = Field(min_length=1)
    required_capabilities: tuple[_NonEmptyStr, ...]
    graph: GraphSpec
    resolved_contracts: tuple[ResolvedContractSpec, ...]
    resolved_policies: tuple[ResolvedPolicySpec, ...]

    @field_validator(
        "contract_digests",
        "source_manifest",
        "required_capabilities",
        "resolved_contracts",
        "resolved_policies",
        mode="before",
    )
    @classmethod
    def freeze_sequences(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @classmethod
    def build(
        cls,
        *,
        graph: GraphSpec,
        resolved_contracts: tuple[ResolvedContractSpec, ...],
        resolved_policies: tuple[ResolvedPolicySpec, ...],
        source_manifest: tuple[SourceManifestEntry, ...],
    ) -> Self:
        canonical_graph = _canonicalize_graph(graph)
        canonical_contracts = _canonicalize_contracts(resolved_contracts)
        canonical_policies = _canonicalize_policies(resolved_policies)
        canonical_manifest = tuple(
            sorted(source_manifest, key=lambda source: (source.source_kind, source.source_id))
        )
        return cls(
            artifact_schema_version=ARTIFACT_SCHEMA_VERSION,
            package_version=PACKAGE_VERSION,
            graph_digest=_semantic_digest(canonical_graph.model_dump(mode="json")),
            policy_digest=_semantic_digest(
                [policy.model_dump(mode="json") for policy in canonical_policies]
            ),
            contract_digests=_contract_digest_index(canonical_contracts),
            source_manifest=canonical_manifest,
            required_capabilities=_required_capabilities(canonical_policies),
            graph=canonical_graph,
            resolved_contracts=canonical_contracts,
            resolved_policies=canonical_policies,
        )

    def canonical_json(self) -> str:
        """Serialize the complete envelope deterministically with one final newline."""
        try:
            serialized = json.dumps(
                self.model_dump(mode="json"),
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"artifact cannot be serialized as canonical JSON: {exc}") from exc
        return serialized + "\n"

    @model_validator(mode="after")
    def validate_integrity_and_canonicality(self) -> Self:
        if self.artifact_schema_version != ARTIFACT_SCHEMA_VERSION:
            raise ValueError(
                "artifact_schema_version must be " f"{ARTIFACT_SCHEMA_VERSION!r}"
            )
        if self.package_version != PACKAGE_VERSION:
            raise ValueError(f"package_version must be {PACKAGE_VERSION!r}")
        if self.graph.graph.graph_schema_version != GRAPH_SCHEMA_VERSION:
            raise ValueError(f"graph_schema_version must be {GRAPH_SCHEMA_VERSION!r}")
        incompatible_policies = sorted(
            policy.requested_reference
            for policy in self.resolved_policies
            if policy.policy_schema_version != POLICY_SCHEMA_VERSION
        )
        if incompatible_policies:
            raise ValueError(
                "resolved policy schema versions must be "
                f"{POLICY_SCHEMA_VERSION!r}: {', '.join(incompatible_policies)}"
            )

        canonical_graph = _canonicalize_graph(self.graph)
        if self.graph != canonical_graph:
            raise ValueError("graph must use canonical semantic ordering")
        canonical_contracts = _canonicalize_contracts(self.resolved_contracts)
        if self.resolved_contracts != canonical_contracts:
            raise ValueError("resolved_contracts must use canonical ordering")
        canonical_policies = _canonicalize_policies(self.resolved_policies)
        if self.resolved_policies != canonical_policies:
            raise ValueError("resolved_policies must use canonical ordering")

        for contract in self.resolved_contracts:
            contract.verify_integrity()
        contract_references = [
            contract.requested_reference for contract in self.resolved_contracts
        ]
        if len(set(contract_references)) != len(contract_references):
            raise ValueError("resolved contract references must be unique")
        graph_contract_references = set(self.graph.contracts)
        for node in self.graph.nodes:
            if isinstance(node, AgentNodeSpec):
                graph_contract_references.update((node.input_contract, node.output_contract))
        if set(contract_references) != graph_contract_references:
            raise ValueError("resolved contracts must exactly match graph contract references")

        policy_references = [policy.requested_reference for policy in self.resolved_policies]
        if len(set(policy_references)) != len(policy_references):
            raise ValueError("resolved policy references must be unique")
        if set(policy_references) != set(self.graph.policies):
            raise ValueError("resolved policies must exactly match graph policy references")

        expected_contract_digests = _contract_digest_index(self.resolved_contracts)
        if self.contract_digests != expected_contract_digests:
            raise ValueError("contract_digests do not match resolved_contracts")
        expected_graph_digest = _semantic_digest(self.graph.model_dump(mode="json"))
        if self.graph_digest != expected_graph_digest:
            raise ValueError("graph_digest does not match the canonical graph")
        expected_policy_digest = _semantic_digest(
            [policy.model_dump(mode="json") for policy in self.resolved_policies]
        )
        if self.policy_digest != expected_policy_digest:
            raise ValueError("policy_digest does not match resolved_policies")
        expected_capabilities = _required_capabilities(self.resolved_policies)
        if self.required_capabilities != expected_capabilities:
            raise ValueError("required_capabilities do not match effective policies")

        canonical_manifest = tuple(
            sorted(
                self.source_manifest,
                key=lambda source: (source.source_kind, source.source_id),
            )
        )
        if self.source_manifest != canonical_manifest:
            raise ValueError("source_manifest must use canonical ordering")
        source_keys = [
            (source.source_kind, source.source_id) for source in self.source_manifest
        ]
        if len(set(source_keys)) != len(source_keys):
            raise ValueError("source_manifest entries must be unique")
        graph_sources = [
            source for source in self.source_manifest if source.source_kind == "graph"
        ]
        if len(graph_sources) != 1:
            raise ValueError("source_manifest must contain exactly one graph source")
        return self
