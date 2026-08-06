"""Render validated graph specifications as Mermaid flowcharts."""

from pathlib import Path

import yaml

from ai_engineering_harness.contracts import (
    AgentNodeSpec,
    DeterministicNodeSpec,
    GraphSpec,
    HumanApprovalNodeSpec,
)


class GraphVisualizer:
    """Render only the explicit nodes, terminals, and edges in a ``GraphSpec``."""

    @classmethod
    def render_mermaid(cls, graph_spec_path: Path) -> str:
        if not graph_spec_path.is_file():
            raise FileNotFoundError(f"graph specification not found: {graph_spec_path}")

        data = yaml.safe_load(graph_spec_path.read_text(encoding="utf-8"))
        graph = GraphSpec.model_validate(data)
        node_aliases = {node.id: f"node_{index}" for index, node in enumerate(graph.nodes)}
        terminal_aliases = {
            terminal.id: f"terminal_{index}"
            for index, terminal in enumerate(graph.terminal_states)
        }
        aliases = node_aliases | terminal_aliases

        lines = [
            "flowchart TD",
            f'    subgraph Workflow ["Workflow: {cls._escape(graph.graph.name)}"]',
        ]
        for node in graph.nodes:
            detail = cls._node_detail(node)
            label = cls._escape(f"{node.id} ({detail})")
            lines.append(f'        {node_aliases[node.id]}["{label}"]')
        for terminal in graph.terminal_states:
            label = cls._escape(f"{terminal.id} ({terminal.outcome})")
            lines.append(f'        {terminal_aliases[terminal.id]}(["{label}"])')
        for node in graph.nodes:
            source = node_aliases[node.id]
            lines.append(f"        {source} -->|success| {aliases[node.on_success]}")
            lines.append(f"        {source} -->|failure| {aliases[node.on_failure]}")
        lines.append("    end")
        return "\n".join(lines)

    @staticmethod
    def _node_detail(
        node: AgentNodeSpec | DeterministicNodeSpec | HumanApprovalNodeSpec,
    ) -> str:
        if isinstance(node, AgentNodeSpec):
            return node.role
        if isinstance(node, DeterministicNodeSpec):
            return node.executor
        return f"human approval: {node.approval_strategy}"

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', "\\\"").replace("\n", " ")
