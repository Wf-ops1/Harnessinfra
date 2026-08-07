"""Testes unitários para verificação do CLI Runtime, FSM State, Visualizer e Audit Export."""

from pathlib import Path

from click.testing import CliRunner

from ai_engineering_harness.cli.main import main
from ai_engineering_harness.compiler.visualizer import GraphVisualizer
from ai_engineering_harness.runtime import RuntimeGraphConfigurationError


def test_graph_visualizer(tmp_path: Path):
    spec_file = tmp_path / "test_graph.yaml"
    spec_file.write_text("""
graph:
  name: test-workflow
  graph_schema_version: "1.0"
  definition_version: "1.0.0"
  entrypoint: step_1
  status: stable
nodes:
  - id: step_1
    type: agent
    role: Amelia
    input_contract: Input
    output_contract: Output
    on_success: step_2
    on_failure: failed
  - id: step_2
    type: agent
    role: Winston
    input_contract: Input
    output_contract: Output
    on_success: completed
    on_failure: failed
terminal_states:
  - id: completed
    outcome: success
  - id: failed
    outcome: failure
policies: []
contracts: []
""", encoding="utf-8")

    mermaid_output = GraphVisualizer.render_mermaid(spec_file)
    assert "flowchart TD" in mermaid_output
    assert "step_1 (Amelia)" in mermaid_output
    assert "step_2 (Winston)" in mermaid_output
    assert "node_0 -->|success| node_1" in mermaid_output
    assert "node_0 -->|failure| terminal_1" in mermaid_output

def test_cli_compile_with_render(tmp_path: Path):
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        spec_file = Path("sample.yaml")
        spec_file.write_text("""
graph:
  name: sample
  graph_schema_version: "1.0"
  definition_version: "1.0.0"
  entrypoint: verify
  status: stable
nodes:
  - id: verify
    type: deterministic
    executor: deterministic_gate
    gate_name: sample
    on_success: completed
    on_failure: failed
terminal_states:
  - id: completed
    outcome: success
  - id: failed
    outcome: failure
policies: []
contracts: []
""", encoding="utf-8")
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
        assert res_run.exit_code != 0
        assert isinstance(res_run.exception, RuntimeGraphConfigurationError)
        assert "Execução iniciada" in res_run.output
        assert "finalizado" not in res_run.output
        execution_root = Path(".harness/state/executions")
        assert list(execution_root.iterdir()) == []
