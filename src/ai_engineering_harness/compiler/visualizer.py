"""Visualizador de Grafos de Execução em Sintaxe Mermaid."""

from pathlib import Path

import yaml


class GraphVisualizer:
    """Converte especificações YAML de Grafos em Diagramas Mermaid Flowchart."""

    @classmethod
    def render_mermaid(cls, graph_spec_path: Path) -> str:
        if not graph_spec_path.exists():
            return "flowchart TD\n    Error[\"Arquivo de especificação não encontrado\"]"

        data = yaml.safe_load(graph_spec_path.read_text(encoding="utf-8")) or {}
        workflow_name = data.get("name", graph_spec_path.stem)
        nodes = data.get("nodes", [])

        lines = [
            "flowchart TD",
            f"    subgraph Workflow_{workflow_name} [Workflow: {workflow_name}]"
        ]

        # Mapeia os nós e conexões
        for i, node in enumerate(nodes):
            node_id = node.get("id", f"node_{i}")
            agent = node.get("agent", "System")
            action = node.get("action", node.get("name", node_id))
            label = f"{node_id}[\"{agent}: {action}\"]"
            lines.append(f"        {label}")

            # Próximo nó na sequência simples ou transições condicionais
            next_node = node.get("next")
            if next_node:
                lines.append(f"        {node_id} --> {next_node}")
            elif i < len(nodes) - 1:
                next_default = nodes[i + 1].get("id", f"node_{i+1}")
                lines.append(f"        {node_id} --> {next_default}")

        lines.append("    end")
        return "\n".join(lines)
