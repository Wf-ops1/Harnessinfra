"""Testes unitários para o módulo StackDetector (TASK-1.4)."""

from pathlib import Path
from ai_engineering_harness.core.detector import StackDetector

def test_detect_python_stack(tmp_path: Path):
    (tmp_path / "pyproject.toml").touch()
    detector = StackDetector(project_root=tmp_path)
    stack = detector.detect()
    assert stack.language == "python"
    assert stack.test_runner == "pytest"

def test_detect_node_stack(tmp_path: Path):
    (tmp_path / "package.json").touch()
    detector = StackDetector(project_root=tmp_path)
    stack = detector.detect()
    assert stack.language == "typescript/javascript"
    assert stack.linter == "eslint"

def test_detect_go_stack(tmp_path: Path):
    (tmp_path / "go.mod").touch()
    detector = StackDetector(project_root=tmp_path)
    stack = detector.detect()
    assert stack.language == "go"
    assert stack.package_manager == "go modules"

def test_detect_rust_stack(tmp_path: Path):
    (tmp_path / "Cargo.toml").touch()
    detector = StackDetector(project_root=tmp_path)
    stack = detector.detect()
    assert stack.language == "rust"

def test_detect_java_stack(tmp_path: Path):
    (tmp_path / "pom.xml").touch()
    detector = StackDetector(project_root=tmp_path)
    stack = detector.detect()
    assert stack.language == "java"
    assert stack.package_manager == "maven"
