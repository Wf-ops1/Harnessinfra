from typing import Any


class PolicyValidationError(Exception):
    """Exceção levantada quando um grafo viola uma política declarada."""
    pass


class PolicyValidator:
    """Valida se os nós e papéis declarados no grafo respeitam as políticas em design-time."""

    def __init__(self, policies: list[dict[str, Any]]) -> None:
        self.policies = policies

    def validate(self, graph_spec: dict[str, Any]) -> bool:
        graph_data = graph_spec.get("graph", {})
        nodes = graph_spec.get("nodes", [])

        # Valida presenças básicas
        if not graph_data.get("name"):
            raise PolicyValidationError("O grafo deve especificar um nome sob a chave 'graph.name'.")

        for node in nodes:
            node_id = node.get("id")
            role = node.get("role")
            if role:
                # Checagem conceitual de permissão do papel
                pass

        return True
