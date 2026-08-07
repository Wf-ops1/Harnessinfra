"""Testes unitários para a narrativa agent-centric e componentes do novo ciclo."""

import json
from pathlib import Path

import pytest

from ai_engineering_harness.cli.commands.rollback import RollbackManager
from ai_engineering_harness.compiler.compiler import GraphCompiler
from ai_engineering_harness.contracts.execution import ExecutionState
from ai_engineering_harness.models.router import ModelRouter
from ai_engineering_harness.observability.audit import AuditTrailManager
from ai_engineering_harness.runtime.agent_executor import AgentExecutor
from ai_engineering_harness.runtime.context_assembler import ContextAssembler, InsufficientContextError
from ai_engineering_harness.runtime.engine import (
    RuntimeEngine,
    RuntimeGraphConfigurationError,
)
from ai_engineering_harness.runtime.planner import PlanDocument, Planner
from ai_engineering_harness.runtime.state_machine import (
    WorkflowState,
    WorkflowStateMachine,
)
from ai_engineering_harness.tools.router import ToolRouter


def _write_runtime_graph(project_root: Path, workflow_name: str) -> Path:
    graph_path = project_root / "spec.yaml"
    graph_path.write_text(
        f"""
graph:
  name: {workflow_name}
  graph_schema_version: "1.0"
  definition_version: "1.0.0"
  entrypoint: step1
  status: stable
nodes:
  - id: step1
    type: deterministic
    executor: deterministic_gate
    gate_name: test
    on_success: completed
    on_failure: failed
terminal_states:
  - id: completed
    outcome: success
  - id: failed
    outcome: failure
policies: []
contracts: []
""",
        encoding="utf-8",
    )
    return graph_path


def test_context_assembly_produces_context_json(tmp_path: Path):
    assembler = ContextAssembler(project_root=tmp_path)
    pkg = assembler.assemble(execution_id="exec-ctx-1", intent="Add logging")
    assert pkg.confidence_score >= 0.72
    
    ctx_file = tmp_path / ".harness" / "state" / "executions" / "exec-ctx-1" / "context.json"
    assert ctx_file.is_file()
    data = json.loads(ctx_file.read_text(encoding="utf-8"))
    assert "confidence_score" in data


def test_context_sufficiency_blocks_when_below_threshold(tmp_path: Path):
    assembler = ContextAssembler(project_root=tmp_path)
    with pytest.raises(InsufficientContextError):
        assembler.assemble(execution_id="exec-ctx-low", intent="Add logging", force_confidence=0.5)


def test_planner_produces_plan_json(tmp_path: Path):
    assembler = ContextAssembler(project_root=tmp_path)
    pkg = assembler.assemble(execution_id="exec-plan-1", intent="Add authentication")
    
    planner = Planner(project_root=tmp_path)
    plan = planner.create_plan(execution_id="exec-plan-1", context_package=pkg, intent="Add authentication")
    
    assert plan.goal == "Add authentication"
    plan_file = tmp_path / ".harness" / "state" / "executions" / "exec-plan-1" / "plan.json"
    assert plan_file.is_file()


def test_plan_validated_before_execution(tmp_path: Path):
    planner = Planner(project_root=tmp_path)
    invalid_plan = PlanDocument(goal="", affected_modules=[], applicable_gates=[])
    assert planner.validate_plan(invalid_plan) is False


def test_agent_dispatches_via_tool_router(tmp_path: Path):
    dummy_file = tmp_path / "dummy.py"
    dummy_file.touch()
    tool_router = ToolRouter(allowed_tools=["serena_edit"])
    model_router = ModelRouter(allowed_providers=["local"])
    executor = AgentExecutor("Amelia", model_router, tool_router=tool_router, project_root=tmp_path)
    
    res = executor.execute_tool("serena_edit", {"file_path": str(dummy_file), "changes": {}})
    assert res is not None


def test_tool_router_blocks_unauthorized_tool(tmp_path: Path):
    tool_router = ToolRouter(allowed_tools=["serena_edit"])
    model_router = ModelRouter(allowed_providers=["local"])
    executor = AgentExecutor("Amelia", model_router, tool_router=tool_router, project_root=tmp_path)
    
    with pytest.raises(PermissionError):
        executor.execute_tool("terminal_run", {"command": "dir", "cwd": "."})


def test_runtime_requires_explicit_graph_executor(tmp_path: Path):
    engine = RuntimeEngine(project_root=tmp_path, execution_id="exec-loop-1", allowed_providers=["local"])
    with pytest.raises(RuntimeGraphConfigurationError, match="GraphExecutor"):
        engine.run_workflow(tmp_path / "missing.json", initial_input={})
    assert not (tmp_path / ".harness").exists()


def test_fsm_legacy_path_constructor_fails_closed(tmp_path: Path):
    assert WorkflowState is ExecutionState
    with pytest.raises(TypeError, match="EventJournalStateStorageProvider"):
        WorkflowStateMachine(tmp_path, "exec-fsm-invalid")
    assert not (tmp_path / ".harness").exists()


def test_runtime_no_longer_runs_fixed_post_verification_sequence(tmp_path: Path):
    yaml_spec = _write_runtime_graph(tmp_path, "seq_workflow")
    compiler = GraphCompiler(project_root=tmp_path)
    compiled_maf = compiler.compile_graph(yaml_spec, "seq_workflow")
    
    engine = RuntimeEngine(project_root=tmp_path, execution_id="exec-seq-1", allowed_providers=["local"])
    with pytest.raises(RuntimeGraphConfigurationError, match="GraphExecutor"):
        engine.run_workflow(compiled_maf, approval_required=False, initial_input={})

    evidence_file = tmp_path / ".harness" / "state" / "executions" / "exec-seq-1" / "evidence.json"
    assert not evidence_file.exists()


def test_rollback_does_not_alter_audit_journal(tmp_path: Path):
    audit = AuditTrailManager(project_root=tmp_path, execution_id="exec-rollback-audit")
    audit.log_event("STEP_1", {"data": "ok"})
    
    initial_content = audit.journal_file.read_text(encoding="utf-8")
    
    rb_mgr = RollbackManager(project_root=tmp_path)
    rb_mgr.execute_rollback("exec-rollback-audit", is_promoted=False)
    
    new_content = audit.journal_file.read_text(encoding="utf-8")
    assert initial_content in new_content


def test_audit_append_only_after_rollback(tmp_path: Path):
    rb_mgr = RollbackManager(project_root=tmp_path)
    rb_mgr.execute_rollback("exec-rollback-integrity", is_promoted=False)
    
    audit = AuditTrailManager(project_root=tmp_path, execution_id="exec-rollback-integrity")
    is_valid, _ = audit.verify_integrity()
    assert is_valid is True
