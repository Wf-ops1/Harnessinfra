"""Compilador estático de grafos em YAML para artefatos MAF JSON versionados com loops governados."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
import yaml

class GraphCompiler:
    """Compila e valida grafos YAML gerando MAF JSON executável em .harness/state/compiled/."""

    HARNESS_VERSION = "0.1.0"
    ARTIFACT_SCHEMA_VERSION = "1.0"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.output_dir = project_root / ".harness" / "state" / "compiled"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_loops(self, graph_spec: Dict[str, Any]) -> None:
        """Valida que todos os loops no grafo possuem limites e condições de parada."""
        nodes = graph_spec.get("nodes", {})
        nodes_iterable = []
        if isinstance(nodes, dict):
            nodes_iterable = [(k, v) for k, v in nodes.items()]
        elif isinstance(nodes, list):
            nodes_iterable = [(n.get("id", f"node_{i}"), n) for i, n in enumerate(nodes) if isinstance(n, dict)]

        for node_id, node_data in nodes_iterable:
            if "loop" in node_data:
                loop = node_data["loop"]
                if "max_iterations" not in loop or "exit_conditions" not in loop:
                    raise ValueError(
                        f"[COMPILER ERROR] Nó '{node_id}' possui um loop sem 'max_iterations' ou 'exit_conditions' limítrofes."
                    )


    def compile_graph(self, yaml_path: Path, workflow_name: str) -> Path:
        """Lê o arquivo YAML, valida e injeta o cabeçalho de versão desacoplado."""
        if not yaml_path.is_file():
            raise FileNotFoundError(f"Especificação de grafo não encontrada: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            graph_spec = yaml.safe_load(f) or {}

        # Validação de loops governados
        self.validate_loops(graph_spec)

        compiled_artifact = {
            "header": {
                "artifact_schema_version": self.ARTIFACT_SCHEMA_VERSION,
                "harness_version": self.HARNESS_VERSION,
                "compiler_version": self.HARNESS_VERSION,
                "runtime_provider": "maf",
                "runtime_adapter_version": "0.1.0",
                "workflow": workflow_name,
                "compiled_at_iso": datetime.now(timezone.utc).isoformat()
            },
            "graph": graph_spec
        }

        output_file = self.output_dir / f"{workflow_name}.json"
        output_file.write_text(json.dumps(compiled_artifact, indent=2), encoding="utf-8")
        return output_file
