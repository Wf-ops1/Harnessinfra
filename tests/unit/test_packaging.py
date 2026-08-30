"""Testes unitários para verificação do empacotamento e recursos nativos (TASK-1.1)."""

import importlib
import importlib.metadata
import importlib.resources
import tomllib
from pathlib import Path

from click.testing import CliRunner

from ai_engineering_harness import __version__
from ai_engineering_harness.cli.main import main

ROOT = Path(__file__).resolve().parents[2]


def test_package_version_surfaces_match_installed_metadata():
    installed_version = importlib.metadata.version("ai-engineering-harness")

    assert __version__ == installed_version

    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"harness, version {installed_version}"

def test_importlib_defaults_resources():
    defaults_files = importlib.resources.files("ai_engineering_harness.defaults")
    assert defaults_files.joinpath("policies").joinpath("verification_policy.yaml").is_file()
    assert defaults_files.joinpath("profiles").joinpath("default.yaml").is_file()


def test_init_reads_traversable_resources_and_preserves_user_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cli_module = importlib.import_module("ai_engineering_harness.cli.main")
    resource_root = tmp_path / "installed-resources"
    (resource_root / "policies").mkdir(parents=True)
    (resource_root / "graphs").mkdir()
    (resource_root / "tools").mkdir()
    (resource_root / "agents" / "example").mkdir(parents=True)
    (resource_root / "policies" / "verification_policy.yaml").write_text(
        "package-policy\n",
        encoding="utf-8",
    )
    (resource_root / "graphs" / "new-feature.yaml").write_text("graph: {}\n", encoding="utf-8")
    (resource_root / "tools" / "tool_registry.yaml").write_text("tools: []\n", encoding="utf-8")
    (resource_root / "agents" / "example" / "agent.yaml").write_text("id: example\n", encoding="utf-8")

    project = tmp_path / "external-project"
    protected = project / ".harness" / "policies" / "verification_policy.yaml"
    protected.parent.mkdir(parents=True)
    protected.write_text("user-policy\n", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setattr(cli_module, "package_files", lambda _package: resource_root)

    result = CliRunner().invoke(cli_module.main, ["init"])

    assert result.exit_code == 0, result.output
    assert protected.read_text(encoding="utf-8") == "user-policy\n"
    assert (project / ".harness" / "graphs" / "specs" / "new-feature.yaml").is_file()
    assert (project / ".harness" / "tools" / "tool_registry.yaml").is_file()
    assert (project / ".harness" / "agents" / "example" / "agent.yaml").is_file()


def test_release_metadata_and_documents_are_consistent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE"]
    assert all(not classifier.startswith("License ::") for classifier in project["classifiers"])
    assert project["urls"]["Changelog"].endswith("/blob/main/CHANGELOG.md")
    assert project["urls"]["Support"].endswith("/blob/main/SUPPORT.md")
    assert "Apache License" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert (ROOT / "CHANGELOG.md").is_file()
    assert (ROOT / "SUPPORT.md").is_file()
    assert (ROOT / "docs" / "portability.md").is_file()


def test_wheel_smoke_is_external_and_accepts_an_explicit_artifact() -> None:
    smoke = (ROOT / "tests" / "ci" / "smoke_wheel.py").read_text(encoding="utf-8")

    assert "TemporaryDirectory" in smoke
    assert "cwd=external_root" in smoke
    assert "cwd=ROOT" not in smoke
    assert 'parser.add_argument("wheel"' in smoke
    assert "HARNESS_TEST_UV" in smoke
