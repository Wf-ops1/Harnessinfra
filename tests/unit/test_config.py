"""Testes unitários para o módulo ConfigResolver em 6 níveis (TASK-1.3)."""

from pathlib import Path

from ai_engineering_harness.core.config import ConfigResolver


def test_config_resolver_hierarchy(tmp_path: Path):
    # Setup .harness structure
    harness_dir = tmp_path / ".harness"
    harness_dir.mkdir()
    
    # 3. project.yaml
    project_yaml = harness_dir / "project.yaml"
    project_yaml.write_text("language: python\nframework: pytest\n", encoding="utf-8")

    # 4. Team Override
    custom_dir = harness_dir / "bmad" / "custom"
    custom_dir.mkdir(parents=True)
    (custom_dir / "team.toml").write_text('context_sufficiency_threshold = 0.80\n', encoding="utf-8")

    # 5. User Override
    (custom_dir / "developer.user.toml").write_text('context_sufficiency_threshold = 0.85\n', encoding="utf-8")

    resolver = ConfigResolver(project_root=tmp_path)
    
    # Test User Override wins over Team & Defaults
    config = resolver.resolve(cli_overrides=None)
    assert config["context_sufficiency_threshold"] == 0.85
    assert config["project"]["language"] == "python"

    # Test CLI Override wins over User Override
    cli_config = resolver.resolve(cli_overrides={"context_sufficiency_threshold": 0.95})
    assert cli_config["context_sufficiency_threshold"] == 0.95
