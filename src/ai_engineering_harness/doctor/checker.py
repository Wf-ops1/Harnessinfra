"""Orquestrador do comando harness doctor."""


from ai_engineering_harness.doctor.probes import ComponentProbeResult, HealthProbe


class DoctorChecker:
    """Orquestra os testes dos componentes do Harness."""

    def __init__(self, config: dict):
        self.config = config

    def check_all(self) -> list[ComponentProbeResult]:
        components = ["Serena MCP", "Codebase-Memory MCP", "Git CLI", "LLM Providers"]
        results = []
        for comp in components:
            results.append(HealthProbe.probe_component(comp, self.config))
        return results
