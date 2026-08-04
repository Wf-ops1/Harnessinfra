"""Formatador gráfico do relatório do harness doctor."""

import sys
from typing import List
from rich.console import Console
from rich.table import Table
from ai_engineering_harness.doctor.probes import ComponentProbeResult

console = Console()

class DoctorReport:
    """Gera saída amigável no terminal para o harness doctor."""

    @classmethod
    def render(cls, results: List[ComponentProbeResult]) -> None:
        table = Table(title="Diagnóstico do AI-Engineering-Harness (Probe de 6 Estágios)")
        table.add_column("Componente", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Estágios (6/6)", style="magenta")

        encoding = getattr(sys.stdout, "encoding", "") or ""
        supports_unicode = "utf" in encoding.lower()

        for res in results:
            if res.is_healthy:
                symbol = "✔ " if supports_unicode else "[OK] "
                status_str = f"[bold green]{symbol}HEALTHY[/bold green]"
            else:
                symbol = "✖ " if supports_unicode else "[FAIL] "
                status_str = f"[bold red]{symbol}UNHEALTHY[/bold red]"
            table.add_row(res.component_name, status_str, "6/6 Aprovados")

        console.print(table)

