"""Testes unitários para verificação do empacotamento e recursos nativos (TASK-1.1)."""

import importlib.resources

from ai_engineering_harness import __version__


def test_package_version():
    assert __version__ == "0.1.0"

def test_importlib_defaults_resources():
    defaults_files = importlib.resources.files("ai_engineering_harness.defaults")
    assert defaults_files.joinpath("policies").joinpath("verification_policy.yaml").is_file()
    assert defaults_files.joinpath("profiles").joinpath("default.yaml").is_file()
