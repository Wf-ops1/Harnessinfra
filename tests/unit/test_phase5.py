"""Testes unitários para a Fase 5 (Graph Compiler & Verification Engine)."""

import json
from pathlib import Path

import pytest

from ai_engineering_harness.compiler.compiler import GraphCompiler
from ai_engineering_harness.verification.engine import VerificationEngine
from ai_engineering_harness.verification.evaluator import VerificationEvaluator
from ai_engineering_harness.versioning import ARTIFACT_SCHEMA_VERSION, PACKAGE_VERSION


def test_compiler_governed_loops_success(tmp_path: Path):
    yaml_spec = tmp_path / "valid_graph.yaml"
    yaml_spec.write_text("""
nodes:
  step1:
    action: "edit"
    loop:
      max_iterations: 3
      exit_conditions:
        - "all_required_gates_passed"
""", encoding="utf-8")

    compiler = GraphCompiler(project_root=tmp_path)
    output = compiler.compile_graph(yaml_spec, "valid_workflow")
    assert output.is_file()

    compiled_data = json.loads(output.read_text(encoding="utf-8"))
    assert compiled_data["header"]["workflow"] == "valid_workflow"
    assert compiled_data["header"]["artifact_schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert compiled_data["header"]["package_version"] == PACKAGE_VERSION
    assert compiled_data["header"]["compiler_version"] == PACKAGE_VERSION
    assert compiled_data["header"]["runtime_adapter_version"] == PACKAGE_VERSION
    assert "harness_version" not in compiled_data["header"]

def test_compiler_ungoverned_loop_rejection(tmp_path: Path):
    yaml_spec = tmp_path / "invalid_graph.yaml"
    yaml_spec.write_text("""
nodes:
  step1:
    action: "edit"
    loop:
      something_else: True
""", encoding="utf-8")

    compiler = GraphCompiler(project_root=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        compiler.compile_graph(yaml_spec, "invalid_workflow")
    assert "[COMPILER ERROR]" in str(exc_info.value)

def test_verification_evaluator_polyglot():
    py_cmd = VerificationEvaluator.get_command("python", "unit_test")
    assert py_cmd == "pytest"

    ts_cmd = VerificationEvaluator.get_command("typescript/javascript", "lint")
    assert ts_cmd == "eslint ."

    go_cmd = VerificationEvaluator.get_command("go", "typecheck")
    assert go_cmd == "go vet ./..."

def test_verification_engine_run(tmp_path: Path):
    engine = VerificationEngine(language="python", working_dir=tmp_path)
    # Gates aplicáveis para Python
    res = engine.verify(active_gates=["typecheck", "unit_test"])
    assert res.total_gates == 2
