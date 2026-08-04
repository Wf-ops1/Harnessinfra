"""Runner poliglota de tipos abstratos de gate de verificação."""

from pathlib import Path
from typing import List, Dict, Any
from ai_engineering_harness.verification.evaluator import VerificationEvaluator
from ai_engineering_harness.verification.results import GateResult, VerificationSuiteResult
from ai_engineering_harness.tools.adapters.terminal import TerminalAdapter

class GateRunner:
    """Executa verificadores aplicáveis declarados no project.yaml."""

    def __init__(self, language: str, working_dir: Path):
        self.language = language
        self.working_dir = working_dir

    def run_applicable_gates(self, active_gates: List[str]) -> VerificationSuiteResult:
        results = []
        all_passed = True

        for gate in active_gates:
            cmd = VerificationEvaluator.get_command(self.language, gate)
            if not cmd:
                # Gate não aplicável para a linguagem é pulado
                continue

            term_res = TerminalAdapter.run_command(cmd, cwd=str(self.working_dir))
            passed = (term_res["exit_code"] == 0)
            if not passed:
                all_passed = False

            results.append(GateResult(
                gate_type=gate,
                command=cmd,
                passed=passed,
                stdout=term_res["stdout"],
                stderr=term_res["stderr"]
            ))

        return VerificationSuiteResult(
            all_passed=all_passed,
            total_gates=len(results),
            passed_gates=sum(1 for r in results if r.passed),
            gate_results=results
        )
