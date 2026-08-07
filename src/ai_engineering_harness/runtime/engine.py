"""Fail-closed facade for loading and executing compiled graphs."""

from __future__ import annotations

from pathlib import Path

from .graph_executor import GraphExecutionError, GraphExecutionResult, GraphExecutor
from .maf_adapter import MAFAdapter


class RuntimeGraphConfigurationError(GraphExecutionError):
    """The legacy runtime call lacks explicit F2.3 execution dependencies."""


class RuntimeEngine:
    """Load a canonical artifact and delegate traversal to ``GraphExecutor``.

    The legacy constructor arguments remain accepted so existing imports and callers fail
    explicitly at execution time instead of falling back to the removed synthetic workflow.
    Operational CLI wiring, execution creation, approval and resume belong to F2.4/F2.5.
    """

    def __init__(
        self,
        project_root: Path,
        execution_id: str,
        allowed_providers: list[str],
        *,
        graph_executor: GraphExecutor | None = None,
    ) -> None:
        self.project_root = project_root
        self.execution_id = execution_id
        self.allowed_providers = tuple(allowed_providers)
        self.graph_executor = graph_executor

    def run_workflow(
        self,
        compiled_maf_path: Path,
        approval_required: bool = False,
        intent: str = "Execute workflow",
        *,
        initial_input: dict[str, object] | None = None,
    ) -> GraphExecutionResult:
        """Validate the artifact and delegate without legacy side effects."""
        if approval_required:
            raise RuntimeGraphConfigurationError(
                "approval execution belongs to F2.4/F2.5 and is not configured",
                execution_id=self.execution_id,
            )
        if self.graph_executor is None:
            raise RuntimeGraphConfigurationError(
                "GraphExecutor must be supplied explicitly",
                execution_id=self.execution_id,
            )
        if initial_input is None:
            raise RuntimeGraphConfigurationError(
                "initial_input must be supplied explicitly",
                execution_id=self.execution_id,
            )

        artifact = MAFAdapter.load_and_validate(compiled_maf_path)
        return self.graph_executor.execute(
            artifact,
            self.execution_id,
            initial_input,
        )


__all__ = ["RuntimeEngine", "RuntimeGraphConfigurationError"]
