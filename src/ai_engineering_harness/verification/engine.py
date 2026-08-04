"""Verification Engine orquestrador do processo de verificação."""

from pathlib import Path
from typing import List
from ai_engineering_harness.verification.gate_runner import GateRunner
from ai_engineering_harness.verification.results import VerificationSuiteResult

class VerificationEngine:
    """Orquestra a suíte de verificadores determinísticos."""

    def __init__(self, language: str, working_dir: Path):
        self.runner = GateRunner(language, working_dir)

    def verify(self, active_gates: List[str]) -> VerificationSuiteResult:
        return self.runner.run_applicable_gates(active_gates)
