"""Strict, immutable contracts for graph specifications and compiled artifacts."""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from .registry import ResolvedContractSpec

_NonEmptyStr: TypeAlias = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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


class CompiledGraphArtifact(_StrictFrozenModel):
    """Typed artifact envelope with an additive resolved-contract view."""

    artifact_schema_version: _NonEmptyStr
    package_version: _NonEmptyStr
    graph: GraphSpec
    resolved_contracts: tuple[ResolvedContractSpec, ...] = ()

    @field_validator("resolved_contracts", mode="before")
    @classmethod
    def freeze_resolved_contracts(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_resolved_contract_integrity(self) -> Self:
        for contract in self.resolved_contracts:
            contract.verify_integrity()
        return self
