"""Orquestrador do comando harness doctor."""

from typing import List
from ai_engineering_harness.doctor.probes import HealthProbe, ComponentProbeResult

class DoctorChecker:
    """Orquestra os testes dos componentes do Harness."""

    def __init__(self, config: dict):
        self.config = config

    def check_all(self) -> List[ComponentProbeResult]:
        components = ["Serena MCP", "Codebase-Memory MCP", "Git CLI", "LLM Providers"]
        results = []
        for comp in components:
            results.append(HealthProbe.probe_component(comp, self.config))
        return results
