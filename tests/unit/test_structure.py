"""Testes unitários para validar a estrutura do pacote e templates de defaults."""

from pathlib import Path

import click.testing

from ai_engineering_harness.cli.main import main


def test_defaults_agents_templates_exist():
    root = Path(__file__).resolve().parent.parent.parent
    defaults_agents = root / "src" / "ai_engineering_harness" / "defaults" / "agents"
    assert defaults_agents.is_dir()
    assert (defaults_agents / "_base" / "agent_base.yaml").is_file()
    assert (defaults_agents / "architecture_analyst" / "agent.yaml").is_file()
    assert (defaults_agents / "architecture_analyst" / "system_prompt.md").is_file()


def test_defaults_graphs_templates_exist():
    root = Path(__file__).resolve().parent.parent.parent
    defaults_graphs = root / "src" / "ai_engineering_harness" / "defaults" / "graphs"
    assert defaults_graphs.is_dir()
    for graph in ["new-feature.yaml", "bug-fix.yaml", "incident.yaml", "migration.yaml", "refactoring.yaml"]:
        assert (defaults_graphs / graph).is_file()


def test_no_duplicate_contracts_at_root():
    root = Path(__file__).resolve().parent.parent.parent
    assert not (root / "contracts").exists()
    assert not (root / "agents").exists()
    assert not (root / "tools").exists()
    assert not (root / "graphs").exists()
    assert not (root / "policies").exists()


def test_harness_init_copies_templates(tmp_path: Path):
    runner = click.testing.CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res = runner.invoke(main, ["init"])
        assert res.exit_code == 0
        harness_dir = Path.cwd() / ".harness"
        assert (harness_dir / "agents").is_dir()
        assert (harness_dir / "graphs" / "specs").is_dir()
        assert (harness_dir / "policies").is_dir()
        assert (harness_dir / "tools").is_dir()
