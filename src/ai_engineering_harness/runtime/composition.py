"""Canonical production composition for the public ``new-feature`` workflow."""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ai_engineering_harness.contracts import AgentNodeSpec
from ai_engineering_harness.contracts.nodes import NewFeatureExecutionState
from ai_engineering_harness.core import ConfigResolver
from ai_engineering_harness.knowledge import KnowledgeSynchronizer, KnowledgeTransactionError
from ai_engineering_harness.models import CancellationToken, ModelRouter
from ai_engineering_harness.persistence import AtomicFileStateStorage
from ai_engineering_harness.security import TrustEvaluationResult
from ai_engineering_harness.tools import build_operational_tool_router
from ai_engineering_harness.tools.adapters import (
    CommandRequest,
    LocalEditingAdapter,
    TerminalAdapter,
    TerminalAdapterError,
)
from ai_engineering_harness.workspace import (
    ExternalWorktreeManager,
    ProvisionedWorktree,
    WorktreeReferenceError,
    WorktreeValidationError,
)

from .agent_executor import AgentExecutor
from .cancellation import CancellationController
from .execution_lifecycle import ExecutionLifecycleService
from .node_executors import (
    AgentNodeExecutor,
    KnowledgeSyncNodeExecutor,
    NodeExecutionContext,
    NodeExecutionResult,
    NodeExecutorRegistry,
)
from .promotion_manager import PromotionManager
from .rollback_manager import RollbackManager
from .tool_loop import ToolLoopError

_PUBLIC_WORKFLOW = "new-feature"
_OPERATIONAL_TOOLS = (
    "apply_patch",
    "git_diff",
    "git_status",
    "list_files",
    "read_file",
    "run_command",
    "search_text",
)


class PublicCompositionError(RuntimeError):
    """The public workflow could not be composed without weakening authority."""


class _DurableCancellationToken(CancellationToken):
    """Bridge execution-owned cancellation state into provider calls."""

    def __init__(self, controller: CancellationController) -> None:
        super().__init__()
        self._controller = controller

    @property
    def is_cancelled(self) -> bool:
        return super().is_cancelled or self._controller.is_cancelled

    def wait(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while not self.is_cancelled:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            if super().wait(min(remaining, 0.05)):
                return True
        return True


@dataclass(frozen=True, slots=True)
class OperationalAgentBackend:
    """Execute public agent nodes against their durable external worktree."""

    project_root: Path
    worktrees: ExternalWorktreeManager
    trust_boundary: TrustEvaluationResult

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        if context.artifact.graph.graph.name != _PUBLIC_WORKFLOW:
            return NodeExecutionResult.failed(
                context.input_payload,
                code="workflow_not_composed",
                message="no public operational composition is registered for this workflow",
                retryable=False,
            )
        if not isinstance(context.node, AgentNodeSpec) or context.node.role == "knowledge_updater":
            return NodeExecutionResult.failed(
                context.input_payload,
                code="agent_role_not_composed",
                message="the selected node is not an operational model agent",
                retryable=False,
            )
        try:
            state = NewFeatureExecutionState.model_validate(context.input_payload)
            worktree = self._worktree(
                context.execution_id,
                base_commit_sha=context.base_commit_sha,
            )
            boundary = self._worktree_boundary(worktree)
            configuration = self._configuration(context.effective_configuration)
            router = ModelRouter.from_effective_config(
                configuration,
                trust_boundary=boundary,
                budget_boundary=context.budget_boundary,
            )
            cancellation = CancellationController(self.project_root, context.execution_id)
            terminal, terminal_environment = self._terminal(worktree, boundary=boundary)
            tool_router = build_operational_tool_router(
                _OPERATIONAL_TOOLS,
                local_adapter=LocalEditingAdapter(path_guard=worktree.path_guard),
                terminal_adapter=terminal,
                trust_boundary=boundary,
                cancellation=cancellation,
            )
            executor = AgentExecutor(
                context.node.role,
                router,
                tool_router=tool_router,
                project_root=worktree.worktree_path,
            )
            result = executor.execute_tool_loop(
                self._prompt(state, context),
                artifact=context.artifact,
                node_id=context.node.id,
                max_tool_steps=self._max_tool_steps(configuration),
                cancellation_token=_DurableCancellationToken(cancellation),
                tool_effect_recorder=context.tool_effect_recorder,
                budget_boundary=context.budget_boundary,
                trust_boundary=boundary,
            )
            modified_files = self._modified_files(
                terminal,
                environment_names=terminal_environment,
            )
            if not modified_files:
                return NodeExecutionResult.failed(
                    state.model_dump(mode="json"),
                    code="no_worktree_changes",
                    message="the operational agent completed without a worktree change",
                    retryable=False,
                    model_calls=result.model_call_records,
                    tool_executions=result.tool_executions,
                )
            completed = state.model_copy(
                update={
                    "modified_files": modified_files,
                    "summary": result.final_response.content.strip()
                    or "feature changes completed through the governed tool loop",
                }
            )
            return NodeExecutionResult.completed(
                completed.model_dump(mode="json"),
                model_calls=result.model_call_records,
                tool_executions=result.tool_executions,
            )
        except ToolLoopError as exc:
            return NodeExecutionResult.failed(
                context.input_payload,
                code="tool_loop_failed",
                message="the governed tool loop did not complete",
                retryable=False,
                model_calls=exc.model_call_records,
                tool_executions=exc.tool_executions,
            )
        except (
            PublicCompositionError,
            TerminalAdapterError,
            TypeError,
            ValueError,
            ValidationError,
        ):
            return NodeExecutionResult.failed(
                context.input_payload,
                code="public_composition_invalid",
                message="the public operational composition is unavailable or invalid",
                retryable=False,
            )

    def _worktree(
        self,
        execution_id: str,
        *,
        base_commit_sha: str | None,
    ) -> ProvisionedWorktree:
        if base_commit_sha is None:
            raise PublicCompositionError("execution base commit is unavailable")
        try:
            return self.worktrees.load_worktree(execution_id)
        except (WorktreeReferenceError, WorktreeValidationError):
            return self.worktrees.create_worktree(
                execution_id,
                expected_base_commit_sha=base_commit_sha,
            )

    def _configuration(
        self,
        document: dict[str, object] | None,
    ) -> dict[str, object]:
        if document is None:
            raise PublicCompositionError("execution configuration is not an object")
        validated = ConfigResolver.validate_persisted(document)
        return validated

    def _terminal(
        self,
        worktree: ProvisionedWorktree,
        *,
        boundary: TrustEvaluationResult,
    ) -> tuple[TerminalAdapter, tuple[str, ...]]:
        executables = {
            alias: resolved
            for alias in boundary.executable_aliases
            if (resolved := shutil.which(alias)) is not None
        }
        if "git" not in executables:
            raise PublicCompositionError("git executable is unavailable or not granted")
        environment: dict[str, str] = {}
        environment_keys: set[str] = set()
        for grant in boundary.secret_grants:
            normalized_name = grant.name.casefold()
            if normalized_name in environment_keys:
                continue
            value = os.environ.get(grant.name)
            if value is not None:
                environment[grant.name] = value
                environment_keys.add(normalized_name)
        git_environment = tuple(
            grant.name
            for grant in boundary.secret_grants
            if "terminal:git" in grant.consumers and grant.name in environment
        )
        return (
            TerminalAdapter(
                path_guard=worktree.path_guard,
                executables=executables,
                environment=environment,
                trust_boundary=boundary,
            ),
            git_environment,
        )

    @staticmethod
    def _worktree_boundary(worktree: ProvisionedWorktree) -> TrustEvaluationResult:
        boundary = worktree.trust_boundary
        if boundary is None:
            raise PublicCompositionError("worktree trust boundary is unavailable")
        return boundary

    @staticmethod
    def _modified_files(
        terminal: TerminalAdapter,
        *,
        environment_names: tuple[str, ...],
    ) -> tuple[str, ...]:
        outputs: list[str] = []
        for argv in (
            ("git", "--no-pager", "diff", "--name-only", "--"),
            ("git", "ls-files", "--others", "--exclude-standard", "--"),
        ):
            result = terminal.execute(
                CommandRequest(
                    argv=argv,
                    cwd=".",
                    env_allowlist=environment_names,
                )
            )
            if result.exit_code != 0:
                raise PublicCompositionError("worktree diff could not be inspected")
            outputs.extend(
                line.strip() for line in result.stdout.splitlines() if line.strip()
            )
        return tuple(sorted(set(outputs)))

    @staticmethod
    def _max_tool_steps(configuration: dict[str, object]) -> int:
        budget = configuration.get("budget")
        configured = budget.get("max_tool_calls") if isinstance(budget, dict) else None
        if type(configured) is not int or configured < 1:
            raise PublicCompositionError("max_tool_calls is unavailable")
        return min(configured, 32)

    @staticmethod
    def _prompt(
        state: NewFeatureExecutionState,
        context: NodeExecutionContext,
    ) -> str:
        payload = json.dumps(
            state.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
        )
        retry = (
            "none"
            if context.retry_context is None
            else context.retry_context.model_dump_json()
        )
        return (
            "Execute the approved new-feature plan only inside the authorized worktree. "
            "Inspect evidence before editing, use governed tools, make the smallest coherent "
            "change, and do not commit or promote. "
            f"Canonical input: {payload}. Retry context: {retry}."
        )


@dataclass(frozen=True, slots=True)
class OperationalKnowledgeBackend:
    """Commit one execution-bound knowledge transaction inside the worktree."""

    worktrees: ExternalWorktreeManager

    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        try:
            state = NewFeatureExecutionState.model_validate(context.input_payload)
            if not state.modified_files or state.summary is None:
                raise PublicCompositionError("knowledge sync requires proven feature changes")
            worktree = self.worktrees.load_worktree(context.execution_id)
            tx_id = f"{context.execution_id}-knowledge"
            status = KnowledgeSynchronizer(worktree.worktree_path).sync_ki(
                tx_id,
                {
                    "id": state.requirement_id,
                    "title": state.summary,
                    "modified_files": list(state.modified_files),
                },
            )
            if status != "COMMITTED":
                raise PublicCompositionError("knowledge transaction did not commit")
            completed = state.model_copy(update={"knowledge_status": "COMMITTED"})
            return NodeExecutionResult.completed(completed.model_dump(mode="json"))
        except (
            KnowledgeTransactionError,
            PublicCompositionError,
            TypeError,
            ValueError,
            ValidationError,
        ):
            return NodeExecutionResult.failed(
                context.input_payload,
                code="knowledge_sync_failed",
                message="the execution-bound knowledge transaction did not commit",
                retryable=False,
            )


def build_new_feature_lifecycle(
    project_root: Path,
    *,
    project_id: str,
    trust_boundary: TrustEvaluationResult,
) -> ExecutionLifecycleService:
    """Build every production service required by the public workflow."""

    root = Path(project_root).resolve(strict=True)
    if not isinstance(trust_boundary, TrustEvaluationResult):
        raise TypeError("trust_boundary must be a TrustEvaluationResult")
    trust_boundary.require_root(root)
    storage = AtomicFileStateStorage(root)
    worktrees = ExternalWorktreeManager(
        root,
        project_id,
        trust_boundary=trust_boundary,
    )
    executors = NodeExecutorRegistry(
        agent=AgentNodeExecutor(
            OperationalAgentBackend(root, worktrees, trust_boundary)
        ),
        knowledge_sync=KnowledgeSyncNodeExecutor(
            OperationalKnowledgeBackend(worktrees)
        ),
    )
    return ExecutionLifecycleService(
        root,
        storage,
        executors,
        config_resolver=ConfigResolver(root),
        verification_worktree_provider=worktrees.load_worktree,
        promotion_manager=PromotionManager(
            root,
            worktrees,
            trust_boundary=trust_boundary,
        ),
        trust_boundary=trust_boundary,
        worktree_manager=worktrees,
        rollback_manager=RollbackManager(
            root,
            trust_boundary=trust_boundary,
        ),
    )


__all__ = [
    "OperationalAgentBackend",
    "OperationalKnowledgeBackend",
    "PublicCompositionError",
    "build_new_feature_lifecycle",
]
