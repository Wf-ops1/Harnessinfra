import importlib.util
from pathlib import Path
from typing import Any


class ContractValidationError(Exception):
    """Exceção levantada quando um nó referencia um contrato inexistente ou inválido."""
    pass


class ContractValidator:
    """Valida em design-time se todos os schemas Pydantic referenciados nos nós existem e são válidos."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def validate(self, graph_spec: dict[str, Any]) -> bool:
        nodes = graph_spec.get("nodes", [])

        for node in nodes:
            node_id = node.get("id")
            for contract_key in ["input_contract", "output_contract"]:
                contract_ref = node.get(contract_key)
                if contract_ref:
                    self._check_contract_ref(node_id, contract_key, contract_ref)

        return True

    def _check_contract_ref(self, node_id: str, contract_key: str, contract_ref: str) -> None:
        parts = contract_ref.split("#")
        rel_path = parts[0]
        class_name = parts[1] if len(parts) > 1 else None

        file_path = self.root_dir / rel_path
        if not file_path.exists():
            file_path = self.root_dir / "src" / "ai_engineering_harness" / rel_path
        if not file_path.exists():
            file_path = self.root_dir / ".harness" / rel_path
        if not file_path.exists():
            raise ContractValidationError(
                f"Nó '{node_id}' ({contract_key}): Arquivo de contrato '{rel_path}' não foi encontrado."
            )

        if class_name:
            # Tenta carregar dinamicamente para confirmar que a classe Pydantic existe
            try:
                spec = importlib.util.spec_from_file_location("dynamic_contract", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if not hasattr(module, class_name):
                        raise ContractValidationError(
                            f"Nó '{node_id}': Classe '{class_name}' não encontrada em '{rel_path}'."
                        )
            except Exception as e:
                if isinstance(e, ContractValidationError):
                    raise e
                raise ContractValidationError(
                    f"Erro ao carregar contrato '{class_name}' de '{rel_path}': {e}"
                )
