"""Interface CLI unificada final com todos os subcomandos do AI-Engineering-Harness."""

import sys
import json
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from ai_engineering_harness.doctor.checker import DoctorChecker
from ai_engineering_harness.doctor.report import DoctorReport
from ai_engineering_harness.compiler.compiler import GraphCompiler
from ai_engineering_harness.compiler.visualizer import GraphVisualizer
from ai_engineering_harness.indexer.codebase_memory_adapter import CodebaseMemoryAdapter
from ai_engineering_harness.verification.engine import VerificationEngine
from ai_engineering_harness.observability.audit import AuditTrailManager
from ai_engineering_harness.cli.commands.rollback import RollbackManager
from ai_engineering_harness.governance.approval import ApprovalManager
from ai_engineering_harness.runtime.engine import RuntimeEngine
from ai_engineering_harness.core.config import ConfigResolver

console = Console()

def _get_symbol(success: bool) -> str:
    encoding = getattr(sys.stdout, "encoding", "") or ""
    supports_unicode = "utf" in encoding.lower()
    if success:
        return "✔ " if supports_unicode else "[OK] "
    return "✖ " if supports_unicode else "[FAIL] "

@click.group(help="AI-Engineering-Harness - Motor Agentic Autônomo e Instalável")
@click.version_option(version="0.1.0", prog_name="harness")
def main():
    pass

@main.command(help="Inicializa a estrutura .harness/ no repositório local.")
def init():
    harness_dir = Path.cwd() / ".harness"
    (harness_dir / "agents").mkdir(parents=True, exist_ok=True)
    (harness_dir / "graphs" / "specs").mkdir(parents=True, exist_ok=True)
    (harness_dir / "policies").mkdir(parents=True, exist_ok=True)
    (harness_dir / "tools").mkdir(parents=True, exist_ok=True)
    (harness_dir / "bmad" / "custom").mkdir(parents=True, exist_ok=True)
    (harness_dir / "bmad" / "graphs").mkdir(parents=True, exist_ok=True)
    (harness_dir / "knowledge" / "artifacts").mkdir(parents=True, exist_ok=True)
    (harness_dir / "contracts").mkdir(parents=True, exist_ok=True)
    (harness_dir / "state" / "compiled").mkdir(parents=True, exist_ok=True)
    (harness_dir / "state" / "executions").mkdir(parents=True, exist_ok=True)
    (harness_dir / "state" / "structural-index").mkdir(parents=True, exist_ok=True)
    (harness_dir / "state" / "worktree-references").mkdir(parents=True, exist_ok=True)
    (harness_dir / "artifacts" / "executions").mkdir(parents=True, exist_ok=True)

    defaults_dir = Path(__file__).resolve().parent.parent / "defaults"
    if defaults_dir.exists():
        for category, target in [("agents", harness_dir / "agents"), ("graphs", harness_dir / "graphs" / "specs"), ("policies", harness_dir / "policies"), ("tools", harness_dir / "tools")]:
            src_cat = defaults_dir / category
            if src_cat.exists():
                for item in src_cat.glob("*"):
                    dst_item = target / item.name
                    if item.is_file() and not dst_item.exists():
                        shutil.copy2(item, dst_item)
                    elif item.is_dir() and not dst_item.exists():
                        shutil.copytree(item, dst_item)

    project_yaml = harness_dir / "project.yaml"
    if not project_yaml.exists():
        project_yaml.write_text("language: python\nframework: pytest\n", encoding="utf-8")

    console.print(f"[green]{_get_symbol(True)}[/green]Estrutura [bold].harness/[/bold] inicializada com sucesso.")

@main.command(help="Executa os probes de diagnóstico de saúde em 6 estágios.")
def doctor():
    console.print("[bold blue]harness doctor[/bold blue] - Executando Probes Seguros de Saúde...")
    checker = DoctorChecker(config={})
    results = checker.check_all()
    DoctorReport.render(results)

@main.command(help="Compila um grafo YAML em artefato MAF JSON executável.")
@click.argument("graph_spec_path", type=click.Path(exists=True))
@click.option("--workflow", default="new-feature", help="Nome do workflow.")
@click.option("--render", is_flag=True, help="Exibe o diagrama Mermaid visual do grafo.")
def compile(graph_spec_path, workflow, render):
    path_obj = Path(graph_spec_path)
    compiler = GraphCompiler(project_root=Path.cwd())
    out_file = compiler.compile_graph(path_obj, workflow)
    console.print(f"[green]{_get_symbol(True)}[/green]Grafo compilado com sucesso em: [bold]{out_file}[/bold]")

    if render:
        mermaid_code = GraphVisualizer.render_mermaid(path_obj)
        console.print("\n[bold magenta]Diagrama Mermaid do Grafo:[/bold magenta]")
        console.print(f"```mermaid\n{mermaid_code}\n```")

@main.command(help="Atualiza o índice estrutural vinculado ao Git SHA via Codebase-Memory MCP.")
def index():
    adapter = CodebaseMemoryAdapter(project_root=Path.cwd())
    ast_data = adapter.query_ast("get_structure", commit_sha="HEAD")
    console.print(f"[green]{_get_symbol(True)}[/green]Índice estrutural atualizado com sucesso. Símbolos: {len(ast_data.get('symbols', []))}")

@main.command(help="Executa um workflow agentic autônomo.")
@click.argument("workflow_name")
@click.option("--approval-required", is_flag=True, help="Requer aprovação humana prévia para promoção.")
def run(workflow_name, approval_required):
    project_root = Path.cwd()
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_hash = uuid.uuid4().hex[:6]
    execution_id = f"exec-{timestamp_str}-{short_hash}"

    console.print(f"[bold green]harness run {workflow_name}[/bold green] - Execução iniciada. ID: [bold cyan]{execution_id}[/bold cyan]")

    # Verificar se a especificação compilada existe ou auto-compilar
    compiled_dir = project_root / ".harness" / "state" / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    compiled_file = compiled_dir / f"{workflow_name}.json"

    if not compiled_file.exists():
        spec_path = project_root / "graphs" / "specs" / f"{workflow_name}.yaml"
        if spec_path.exists():
            compiler = GraphCompiler(project_root=project_root)
            compiler.compile_graph(spec_path, workflow_name)
        else:
            # Fallback: criar especificação temporária mínima e compilar
            spec_temp = compiled_dir / f"temp_{workflow_name}.yaml"
            spec_temp.write_text(f"name: {workflow_name}\nnodes:\n  - id: step_1\n    agent: Amelia\n", encoding="utf-8")
            compiler = GraphCompiler(project_root=project_root)
            compiler.compile_graph(spec_temp, workflow_name)
            if spec_temp.exists():
                spec_temp.unlink()

    # Executar RuntimeEngine
    engine = RuntimeEngine(project_root=project_root, execution_id=execution_id, allowed_providers=["local", "openai", "anthropic", "google"])
    final_state = engine.run_workflow(compiled_file, approval_required=approval_required)

    # Registrar no AuditTrail
    audit_mgr = AuditTrailManager(project_root=project_root, execution_id=execution_id)
    audit_mgr.log_event("WORKFLOW_COMPLETED", {"workflow": workflow_name, "final_state": final_state})

    console.print(f"[bold green]{_get_symbol(True)}Workflow {workflow_name} finalizado![/bold green] Estado FSM: [bold yellow]{final_state}[/bold yellow]")

@main.command(help="Consulta o status em tempo real de uma execução.")
@click.argument("execution_id")
def status(execution_id):
    project_root = Path.cwd()
    state_file = project_root / ".harness" / "state" / "executions" / execution_id / "workflow-state.json"

    if not state_file.exists():
        console.print(f"[red]{_get_symbol(False)}Execução '{execution_id}' não encontrada em .harness/state/executions/[/red]")
        sys.exit(1)

    data = json.loads(state_file.read_text(encoding="utf-8"))
    table = Table(title=f"Status da Execução {execution_id}")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor", style="bold green")

    table.add_row("Execution ID", data.get("execution_id", execution_id))
    table.add_row("FSM State", data.get("state", "UNKNOWN"))
    table.add_row("Última Atualização", data.get("updated_at_iso", "N/A"))

    console.print(table)

@main.command(help="Inspeciona os detalhes e o histórico de uma execução.")
@click.argument("execution_id")
def inspect(execution_id):
    project_root = Path.cwd()
    exec_dir = project_root / ".harness" / "state" / "executions" / execution_id

    if not exec_dir.exists():
        console.print(f"[red]{_get_symbol(False)}Diretório de execução '{execution_id}' não encontrado.[/red]")
        sys.exit(1)

    state_file = exec_dir / "workflow-state.json"
    fsm_state = "DESCONHECIDO"
    if state_file.exists():
        fsm_state = json.loads(state_file.read_text(encoding="utf-8")).get("state", "DESCONHECIDO")

    audit_mgr = AuditTrailManager(project_root=project_root, execution_id=execution_id)
    is_valid, msg = audit_mgr.verify_integrity()

    approval_mgr = ApprovalManager(project_root=project_root)
    approval_status = approval_mgr.get_approval_status(execution_id) or "NENHUMA"

    console.print(f"[bold cyan]Inspeção Detalhada da Execução {execution_id}:[/bold cyan]")
    console.print(f"  - [bold]Estado FSM:[/bold] {fsm_state}")
    console.print(f"  - [bold]Integridade Hash Chain:[/bold] [{'green' if is_valid else 'red'}]{msg}[/{'green' if is_valid else 'red'}]")
    console.print(f"  - [bold]Status de Aprovação:[/bold] {approval_status}")

@main.command(help="Aprova manualmente a promoção de alterações em estado AWAITING_APPROVAL.")
@click.argument("execution_id")
def approve(execution_id):
    mgr = ApprovalManager(project_root=Path.cwd())
    if mgr.approve(execution_id):
        console.print(f"[green]{_get_symbol(True)}[/green]Execução [bold]{execution_id}[/bold] APROVADA com sucesso.")
    else:
        console.print(f"[red]{_get_symbol(False)}[/red]Falha ao aprovar execução {execution_id}.")

@main.command(help="Executa os verificadores poliglotas aplicáveis ao projeto.")
def verify():
    engine = VerificationEngine(language="python", working_dir=Path.cwd())
    res = engine.verify(active_gates=["typecheck", "unit_test"])
    status_color = "green" if res.all_passed else "red"
    console.print(f"[{status_color}]Verificação concluída. Aprovados: {res.passed_gates}/{res.total_gates}[/{status_color}]")

@main.command(help="Valida a integridade da Hash Chain dos logs de auditoria.")
@click.argument("execution_id")
@click.option("--export", type=click.Choice(["sarif", "json"], case_sensitive=False), help="Exporta os logs de auditoria no formato selecionado.")
def audit(execution_id, export):
    audit_mgr = AuditTrailManager(project_root=Path.cwd(), execution_id=execution_id)
    is_valid, msg = audit_mgr.verify_integrity()

    if export:
        if export.lower() == "sarif":
            out = audit_mgr.export_sarif()
        else:
            out = audit_mgr.export_json()
        console.print(out)
        return

    if is_valid:
        console.print(f"[green]{_get_symbol(True)}[/green][bold]AUDIT SUCCESS:[/bold] {msg}")
    else:
        console.print(f"[red]{_get_symbol(False)}[/red][bold]AUDIT FAILURE:[/bold] {msg}")

@main.command(help="Executa a reversão controlada em duas fases (Código / Efeitos).")
@click.argument("execution_id")
@click.option("--promoted", is_flag=True, help="Indica se a alteração já foi promovida.")
def rollback(execution_id, promoted):
    mgr = RollbackManager(project_root=Path.cwd())
    res = mgr.execute_rollback(execution_id=execution_id, is_promoted=promoted)
    console.print(f"[yellow]Rollback executado:[/yellow] {res['code_message']}")

if __name__ == "__main__":
    main()
