"""Suíte de Testes E2E do Ciclo de Vida do Harness (TASK-8.3)."""

import json
from pathlib import Path

from ai_engineering_harness.compiler.compiler import GraphCompiler
from ai_engineering_harness.core.detector import StackDetector
from ai_engineering_harness.doctor.checker import DoctorChecker
from ai_engineering_harness.indexer.codebase_memory_adapter import CodebaseMemoryAdapter
from ai_engineering_harness.knowledge.synchronizer import KnowledgeSynchronizer
from ai_engineering_harness.observability.audit import AuditTrailManager
from ai_engineering_harness.runtime.engine import RuntimeEngine
from ai_engineering_harness.verification.engine import VerificationEngine


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


def test_full_lifecycle_e2e_python(tmp_path: Path):
    # 1. Setup projeto fixture
    (tmp_path / "pyproject.toml").touch()

    # 2. Detector
    detector = StackDetector(project_root=tmp_path)
    stack = detector.detect()
    assert stack.language == "python"

    # 3. Doctor Probe
    checker = DoctorChecker(config={})
    doctor_results = checker.check_all()
    assert all(r.is_healthy for r in doctor_results)

    # 4. Compile Graph
    yaml_spec = _write_runtime_graph(tmp_path, "new-feature")
    compiler = GraphCompiler(project_root=tmp_path)
    compiled_maf = compiler.compile_graph(yaml_spec, "new-feature")
    assert compiled_maf.is_file()

    # 5. Index Structural
    indexer = CodebaseMemoryAdapter(project_root=tmp_path)
    ast_data = indexer.query_ast("get_structure", commit_sha="commit-e2e-1")
    assert ast_data["commit_sha"] == "commit-e2e-1"

    # 6. Run Workflow
    engine = RuntimeEngine(project_root=tmp_path, execution_id="exec-e2e-100", allowed_providers=["local"])
    final_state = engine.run_workflow(compiled_maf, approval_required=False, intent="Deliver new feature")
    assert final_state.value == "COMPLETED"

    exec_dir = tmp_path / ".harness" / "state" / "executions" / "exec-e2e-100"
    assert (exec_dir / "context.json").is_file()
    assert (exec_dir / "plan.json").is_file()
    assert (exec_dir / "evidence.json").is_file()

    evidence = json.loads((exec_dir / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["execution_id"] == "exec-e2e-100"
    assert "commit_sha" in evidence

    # 7. Verification Engine
    ver_engine = VerificationEngine(language="python", working_dir=tmp_path)
    ver_res = ver_engine.verify(active_gates=["typecheck"])
    assert ver_res.total_gates == 1

    # 8. Re-index & Knowledge Sync
    knw_sync = KnowledgeSynchronizer(project_root=tmp_path)
    tx_status = knw_sync.sync_ki("tx-e2e-1", {"id": "ki-feature-1", "title": "New Feature Done"})
    assert tx_status == "COMMITTED"

    # 9. Audit Trail & Hash Chain Verification
    audit = AuditTrailManager(project_root=tmp_path, execution_id="exec-e2e-100")
    audit.log_event("WORKFLOW_COMPLETED", {"status": "SUCCESS"})
    is_valid, _ = audit.verify_integrity()
    assert is_valid is True
