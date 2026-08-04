"""Testes unitários para a Fase 6 (Runtime, FSM, Approval e Migrations)."""

import json
from pathlib import Path
import pytest
from ai_engineering_harness.runtime.state_machine import WorkflowStateMachine, WorkflowState
from ai_engineering_harness.governance.approval import ApprovalManager
from ai_engineering_harness.runtime.engine import RuntimeEngine
from ai_engineering_harness.compiler.compiler import GraphCompiler

def test_workflow_state_machine_transitions(tmp_path: Path):
    fsm = WorkflowStateMachine(project_root=tmp_path, execution_id="exec-111")
    assert fsm.current_state == WorkflowState.INITIATED
    
    fsm.transition_to(WorkflowState.PLANNING)
    assert fsm.current_state == WorkflowState.PLANNING

    state_file = tmp_path / ".harness" / "state" / "executions" / "exec-111" / "workflow-state.json"
    assert state_file.is_file()
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["state"] == "PLANNING"

def test_approval_manager_flow(tmp_path: Path):
    mgr = ApprovalManager(project_root=tmp_path)
    req_file = mgr.create_approval_request("exec-222", "Precisa aprovação")
    assert req_file.is_file()

    approved = mgr.approve("exec-222")
    assert approved is True
    data = json.loads(req_file.read_text(encoding="utf-8"))
    assert data["status"] == "APPROVED"

def test_runtime_engine_with_approval(tmp_path: Path):
    # Compilar grafo primeiro
    yaml_spec = tmp_path / "graph.yaml"
    yaml_spec.write_text("nodes: {step1: {action: 'test'}}", encoding="utf-8")
    compiler = GraphCompiler(project_root=tmp_path)
    compiled_maf = compiler.compile_graph(yaml_spec, "test_flow")

    engine = RuntimeEngine(project_root=tmp_path, execution_id="exec-333", allowed_providers=["local"])
    final_state = engine.run_workflow(compiled_maf, approval_required=True)

    assert final_state == WorkflowState.AWAITING_APPROVAL
