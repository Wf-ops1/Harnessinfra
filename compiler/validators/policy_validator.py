from typing import Any

from ai_engineering_harness.contracts import PolicyRegistry, PolicyRegistryError


class PolicyValidationError(Exception):
    """Exceção levantada quando um grafo viola uma política declarada."""


class PolicyValidator:
    """Valida se os nós e papéis declarados no grafo respeitam as políticas em design-time."""

    def __init__(self, policies: list[dict[str, Any]]) -> None:
        self.policies = policies

    def validate(self, graph_spec: dict[str, Any]) -> bool:
        graph_data = graph_spec.get("graph", {})

        if not isinstance(graph_data, dict) or not graph_data.get("name"):
            raise PolicyValidationError("O grafo deve especificar um nome sob a chave 'graph.name'.")

        references = graph_spec.get("policies", [])
        if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
            raise PolicyValidationError("O campo 'policies' deve ser uma lista de referências string.")
        if len(references) != len(self.policies):
            raise PolicyValidationError(
                "Nem todas as policies declaradas foram carregadas; referência ausente ou ilegível."
            )

        policy_documents = dict(zip(references, self.policies, strict=True))
        try:
            PolicyRegistry(policy_documents=policy_documents).resolve_legacy_graph(graph_spec)
        except PolicyRegistryError as exc:
            raise PolicyValidationError(str(exc)) from exc
        return True
