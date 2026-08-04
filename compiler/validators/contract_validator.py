"""Compatibility adapter for the package's fail-closed contract registry."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ai_engineering_harness.contracts.registry import ContractRegistry, ContractRegistryError


class ContractValidationError(Exception):
    """Raised when a node references a missing, unsafe, or invalid contract."""


class ContractValidator:
    """Validate legacy graph dictionaries without importing project files by path."""

    def __init__(
        self,
        root_dir: Path,
        *,
        repository_trusted: bool = False,
        approved_python_contracts: Iterable[str] = (),
    ) -> None:
        self.registry = ContractRegistry(
            schema_root=root_dir,
            repository_trusted=repository_trusted,
            approved_python_contracts=approved_python_contracts,
        )

    def validate(self, graph_spec: dict[str, Any]) -> bool:
        nodes = graph_spec.get("nodes", [])
        if not isinstance(nodes, list):
            raise ContractValidationError("O campo 'nodes' deve ser uma lista para validar contratos.")

        for node in nodes:
            if not isinstance(node, dict):
                raise ContractValidationError("Cada nó deve ser um objeto para validar contratos.")
            node_id = node.get("id", "<unknown>")
            for contract_key in ("input_contract", "output_contract"):
                contract_ref = node.get(contract_key)
                if contract_ref is not None:
                    self._check_contract_ref(str(node_id), contract_key, contract_ref)
        return True

    def _check_contract_ref(self, node_id: str, contract_key: str, contract_ref: object) -> None:
        if not isinstance(contract_ref, str):
            raise ContractValidationError(
                f"Nó '{node_id}' ({contract_key}): referência de contrato deve ser string."
            )
        try:
            self.registry.resolve(contract_ref)
        except ContractRegistryError as exc:
            raise ContractValidationError(f"Nó '{node_id}' ({contract_key}): {exc}") from exc
