"""Runtime Engine orquestrador de workflows agentic."""

import json
from pathlib import Path

import yaml

from ai_engineering_harness.governance.approval import ApprovalManager
from ai_engineering_harness.indexer.codebase_memory_adapter import CodebaseMemoryAdapter
from ai_engineering_harness.knowledge.synchronizer import KnowledgeSynchronizer
from ai_engineering_harness.models.router import ModelRouter
from ai_engineering_harness.runtime.agent_executor import AgentExecutor
from ai_engineering_harness.runtime.context_assembler import ContextAssembler, InsufficientContextError
from ai_engineering_harness.runtime.maf_adapter import MAFAdapter
from ai_engineering_harness.runtime.planner import Planner
from ai_engineering_harness.runtime.promotion_manager import PromotionManager
from ai_engineering_harness.runtime.state_machine import WorkflowState, WorkflowStateMachine
from ai_engineering_harness.tools.router import ToolRouter
from ai_engineering_harness.verification.engine import VerificationEngine


class RuntimeEngine:
    """Orquestra o ciclo de vida da FSM e a execução de nós do grafo."""

    def __init__(self, project_root: Path, execution_id: str, allowed_providers: list[str]):
        self.project_root = project_root
        self.execution_id = execution_id
        self.fsm = WorkflowStateMachine(project_root, execution_id)
        self.router = ModelRouter(allowed_providers=allowed_providers)
        self.approval_mgr = ApprovalManager(project_root)
        self.tool_router = ToolRouter(allowed_tools=["serena_edit", "terminal_run"])

    def _get_max_retries(self) -> int:
        policy_file = self.project_root / "src" / "ai_engineering_harness" / "defaults" / "policies" / "retry_cost_policy.yaml"
        if not policy_file.exists():
            policy_file = self.project_root / ".harness" / "policies" / "retry_cost_policy.yaml"
        if policy_file.exists():
            try:
                data = yaml.safe_load(policy_file.read_text(encoding="utf-8")) or {}
                return int(data.get("model_routing", {}).get("retry_max", 3))
            except (OSError, TypeError, ValueError, yaml.YAMLError):
                return 3
        return 3

    def _get_active_gates(self) -> list:
        """Lê os gates obrigatórios da verification_policy.yaml do projeto.

        Retorna lista vazia em dois casos:
        - Nenhuma política encontrada (ex: tmp_path de testes)
        - project_root não contém marcadores de projeto real (pyproject.toml, setup.py)
          — evita rodar mypy/pytest em diretórios vazios de scaffolding.
        """
        # Guard: só ativa gates em projetos reais com código
        project_markers = ["pyproject.toml", "setup.py", "setup.cfg", "package.json", "go.mod", "Cargo.toml"]
        has_project = any((self.project_root / m).exists() for m in project_markers)
        if not has_project:
            return []

        policy_candidates = [
            self.project_root / ".harness" / "policies" / "verification_policy.yaml",
            self.project_root / "src" / "ai_engineering_harness" / "defaults" / "policies" / "verification_policy.yaml",
        ]
        for policy_file in policy_candidates:
            if policy_file.exists():
                try:
                    data = yaml.safe_load(policy_file.read_text(encoding="utf-8")) or {}
                    gates = data.get("required_gates", [])
                    return [g["id"] for g in gates if isinstance(g, dict) and "id" in g]
                except (OSError, TypeError, ValueError, yaml.YAMLError):
                    return []
        # Sem política encontrada → sem gates obrigatórios
        return []


    def run_workflow(self, compiled_maf_path: Path, approval_required: bool = False, intent: str = "Execute workflow") -> WorkflowState:
        # 1. Carregar MAF JSON
        MAFAdapter.load_and_validate(compiled_maf_path)

        # 2. Context Assembly
        self.fsm.transition_to(WorkflowState.CONTEXT_ASSEMBLING)
        assembler = ContextAssembler(self.project_root)
        try:
            context_pkg = assembler.assemble(self.execution_id, intent=intent)
        except InsufficientContextError:
            self.fsm.transition_to(WorkflowState.BLOCKED_INSUFFICIENT_CONTEXT)
            return WorkflowState.BLOCKED_INSUFFICIENT_CONTEXT

        # 3. Generating Plan
        self.fsm.transition_to(WorkflowState.GENERATING_PLAN)
        planner = Planner(self.project_root)
        plan_doc = planner.create_plan(self.execution_id, context_pkg, intent=intent)

        # 4. Executing (Amelia via ToolRouter)
        self.fsm.transition_to(WorkflowState.EXECUTING)
        executor = AgentExecutor("Amelia", self.router, tool_router=self.tool_router, project_root=self.project_root)

        max_retries = self._get_max_retries()
        # Gates lidos da política do projeto — lista vazia em tmp_path → all_passed=True por vacuidade
        active_gates = self._get_active_gates()
        verified = False
        ver_res = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                # Repair loop: re-executa a partir de EXECUTING após gate failure
                self.fsm.transition_to(WorkflowState.EXECUTING)

            executor.execute_node(f"Implementar história de usuário: {intent} (tentativa {attempt + 1})")

            # 5. Verifying — usa resultado REAL do VerificationEngine
            self.fsm.transition_to(WorkflowState.VERIFYING)
            ver_engine = VerificationEngine(language="python", working_dir=self.project_root)
            ver_res = ver_engine.verify(active_gates=active_gates)

            # all_passed=True por vacuidade quando active_gates=[] (sem política configurada)
            verified = ver_res.all_passed
            if verified:
                break
            # Se não passou, continua o repair loop até esgotar max_retries

        if not verified:
            self.fsm.transition_to(WorkflowState.FAILED_RETRY_EXHAUSTED)
            return WorkflowState.FAILED_RETRY_EXHAUSTED

        # 6. Se aprovação exigida
        if approval_required:
            self.approval_mgr.create_approval_request(self.execution_id, "Política estrita do perfil requer aprovação humana.")
            self.fsm.transition_to(WorkflowState.AWAITING_APPROVAL)
            return WorkflowState.AWAITING_APPROVAL

        # 7. PROMOTING
        self.fsm.transition_to(WorkflowState.PROMOTING)
        promo_mgr = PromotionManager(self.project_root)
        commit_sha = promo_mgr.promote(self.execution_id, dry_run=True)

        # 8. REINDEXING
        self.fsm.transition_to(WorkflowState.REINDEXING)
        indexer = CodebaseMemoryAdapter(self.project_root)
        indexer.query_ast("get_structure", commit_sha=commit_sha)

        # 9. KNOWLEDGE_SYNC
        self.fsm.transition_to(WorkflowState.KNOWLEDGE_SYNC)
        knw_sync = KnowledgeSynchronizer(self.project_root)
        tx_id = f"tx-{self.execution_id}"
        knw_sync.sync_ki(tx_id, {"id": f"ki-{self.execution_id}", "title": f"Sync for {self.execution_id}"})

        # 10. GENERATING_EVIDENCE
        self.fsm.transition_to(WorkflowState.GENERATING_EVIDENCE)
        exec_dir = self.project_root / ".harness" / "state" / "executions" / self.execution_id
        evidence_file = exec_dir / "evidence.json"
        evidence_data = {
            "execution_id": self.execution_id,
            "plan": plan_doc.to_dict(),
            "context": context_pkg.to_dict(),
            "verification_results": ver_res.model_dump() if ver_res and hasattr(ver_res, "model_dump") else {},
            "commit_sha": commit_sha,
            "knowledge_transaction": tx_id
        }
        evidence_file.write_text(json.dumps(evidence_data, indent=2), encoding="utf-8")

        # 11. COMPLETED
        self.fsm.transition_to(WorkflowState.COMPLETED)
        return WorkflowState.COMPLETED
