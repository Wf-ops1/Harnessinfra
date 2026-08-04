"""Testes unitários para verificação do empacotamento e recursos nativos (TASK-1.1)."""

import importlib.metadata
import importlib.resources

from click.testing import CliRunner

from ai_engineering_harness import __version__
from ai_engineering_harness.cli.main import main


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
