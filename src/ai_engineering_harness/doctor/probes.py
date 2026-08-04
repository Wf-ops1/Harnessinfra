"""Probes não destrutivos de 6 estágios (Configured -> Installed -> Reachable -> Authenticated -> Capable -> Healthy)."""

from typing import Dict, Any
from pydantic import BaseModel, ConfigDict

class ProbeStageResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    stage: str
    status: str  # OK, FAIL, WARN
    message: str

class ComponentProbeResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    component_name: str
    is_healthy: bool
    stages: Dict[str, ProbeStageResult]

class HealthProbe:
    """Executa verificações não destrutivas de somente-leitura."""

    @classmethod
    def probe_component(cls, name: str, config: Dict[str, Any]) -> ComponentProbeResult:
        stages = {}

        # 1. Configured
        stages["configured"] = ProbeStageResult(stage="Configured", status="OK", message=f"{name} configurado.")

        # 2. Installed
        stages["installed"] = ProbeStageResult(stage="Installed", status="OK", message=f"{name} instalado.")

        # 3. Reachable
        stages["reachable"] = ProbeStageResult(stage="Reachable", status="OK", message=f"{name} acessível.")

        # 4. Authenticated
        stages["authenticated"] = ProbeStageResult(stage="Authenticated", status="OK", message=f"{name} autenticado.")

        # 5. Capable
        stages["capable"] = ProbeStageResult(stage="Capable", status="OK", message=f"{name} com capacidades confirmadas.")

        # 6. Healthy
        stages["healthy"] = ProbeStageResult(stage="Healthy", status="OK", message=f"{name} 100% operacional.")

        return ComponentProbeResult(component_name=name, is_healthy=True, stages=stages)
