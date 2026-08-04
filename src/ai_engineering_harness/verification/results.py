"""Formatador e estruturador de resultados de verificação."""

from pydantic import BaseModel, ConfigDict


class GateResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    gate_type: str
    command: str
    passed: bool
    stdout: str
    stderr: str

class VerificationSuiteResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    all_passed: bool
    total_gates: int
    passed_gates: int
    gate_results: list[GateResult]
