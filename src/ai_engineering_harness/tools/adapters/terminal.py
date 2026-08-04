"""Adaptador para execução segura de comandos no terminal sandbox."""

import subprocess
from typing import Any


class TerminalAdapter:
    """Executor controlado no Terminal Sandbox."""

    @classmethod
    def run_command(cls, command: str, cwd: str, timeout: int = 30) -> dict[str, Any]:
        """Executa um comando de shell capturando stdout e exit code."""
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout
            )
            return {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Comando excedeu o tempo limite de {timeout}s."
            }
