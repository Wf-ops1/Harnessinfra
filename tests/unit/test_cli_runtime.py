"""Testes unitários para verificação do CLI Runtime, FSM State, Visualizer e Audit Export."""

from pathlib import Path

from click.testing import CliRunner

from ai_engineering_harness.cli.main import main
from ai_engineering_harness.compiler.visualizer import GraphVisualizer


def test_graph_visualizer(tmp_path: Path):
    spec_file = tmp_path / "test_graph.yaml"
    spec_file.write_text("""
name: test-workflow
nodes:
  - id: step_1
    agent: Amelia
    action: Code Implementation
  - id: step_2
    agent: Winston
    action: Review Architecture
""", encoding="utf-8")

    mermaid_output = GraphVisualizer.render_mermaid(spec_file)
    assert "flowchart TD" in mermaid_output
    assert "Amelia: Code Implementation" in mermaid_output
    assert "Winston: Review Architecture" in mermaid_output

def test_cli_compile_with_render(tmp_path: Path):
    runner = CliRunner()
    spec_file = tmp_path / "sample.yaml"
    spec_file.write_text("name: sample\nnodes: []", encoding="utf-8")

    with runner.isolated_filesystem():
        res = runner.invoke(main, ["compile", str(spec_file), "--workflow", "sample", "--render"])
        assert res.exit_code == 0
        assert "Grafo compilado com sucesso" in res.output
        assert "Diagrama Mermaid do Grafo" in res.output

def test_cli_run_status_inspect_lifecycle():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # 1. Init
        res_init = runner.invoke(main, ["init"])
        assert res_init.exit_code == 0

        # 2. Run
        res_run = runner.invoke(main, ["run", "new-feature"])
        assert res_run.exit_code == 0
        assert "Execução iniciada" in res_run.output

        # Extrair o ID da execução
        output_lines = res_run.output.split("\n")
        exec_line = next(line for line in output_lines if "ID:" in line or "exec-" in line)
        exec_id = exec_line.split("ID:")[-1].strip()

        # 3. Status
        res_status = runner.invoke(main, ["status", exec_id])
        assert res_status.exit_code == 0
        assert "FSM State" in res_status.output
        assert "COMPLETED" in res_status.output

        # 4. Inspect
        res_inspect = runner.invoke(main, ["inspect", exec_id])
        assert res_inspect.exit_code == 0
        assert "Inspeção Detalhada" in res_inspect.output

        # 5. Audit Export JSON
        res_audit_json = runner.invoke(main, ["audit", exec_id, "--export", "json"])
        assert res_audit_json.exit_code == 0
        assert '"events"' in res_audit_json.output

        # 6. Audit Export SARIF
        res_audit_sarif = runner.invoke(main, ["audit", exec_id, "--export", "sarif"])
        assert res_audit_sarif.exit_code == 0
        assert '"version": "2.1.0"' in res_audit_sarif.output
