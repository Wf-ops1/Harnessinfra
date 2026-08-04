from typing import Any


class GateInjector:
    """Injeta automaticamente os gates determinísticos de verificação (verification_policy.yaml) no grafo compilado."""

    def __init__(self, verification_policy: dict[str, Any]) -> None:
        self.verification_policy = verification_policy

    def inject_gates(self, compiled_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        required_gates = self.verification_policy.get("required_gates", [])

        gate_execution_nodes = []
        for gate in required_gates:
            gate_execution_nodes.append(
                {
                    "id": f"injected_gate_{gate['id']}",
                    "executor": "deterministic_command",
                    "command": gate.get("command"),
                    "blocking": gate.get("blocking", True),
                }
            )

        # Injeta os gates antes da entrega final
        return compiled_nodes + gate_execution_nodes
