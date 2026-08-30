"""F7.C1 contracts for the canonical public ``new-feature`` composition."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_engineering_harness.contracts.nodes import NewFeatureExecutionState
from ai_engineering_harness.runtime import (
    OperationalAgentBackend,
    build_new_feature_lifecycle,
)
from ai_engineering_harness.security import TrustAuthorization, TrustBoundaryEvaluator
from ai_engineering_harness.tools.adapters import CommandResult


def _boundary(project_root: Path):
    return TrustBoundaryEvaluator(
        project_root,
        authorization=TrustAuthorization(
            repository_root=str(project_root.resolve(strict=True)),
            executable_aliases=("git", "python"),
            promotion_allowed=True,
        ),
    ).evaluate()


def test_new_feature_state_freezes_sequences_and_rejects_unsafe_identity() -> None:
    state = NewFeatureExecutionState.model_validate(
        {
            "requirement_id": "req-f7c1",
            "intent": "Deliver the public path",
            "affected_files": ["src/example.py"],
            "acceptance_criteria": ["The public workflow completes"],
        }
    )

    assert state.affected_files == ("src/example.py",)
    assert state.acceptance_criteria == ("The public workflow completes",)
    assert state.modified_files == ()
    assert state.knowledge_status == "PENDING"

    with pytest.raises(ValidationError):
        NewFeatureExecutionState.model_validate(
            {
                "requirement_id": "unsafe requirement",
                "intent": "Deliver",
                "affected_files": ["../escape.py"],
            }
        )

    with pytest.raises(ValidationError):
        NewFeatureExecutionState.model_validate(
            {
                "requirement_id": "req-f7c1",
                "intent": "Deliver",
                "acceptance_criteria": ["same", "same"],
            }
        )


def test_public_factory_registers_every_operational_lifecycle_backend(
    tmp_path: Path,
) -> None:
    boundary = _boundary(tmp_path)
    lifecycle = build_new_feature_lifecycle(
        tmp_path,
        project_id="f7c1-unit",
        trust_boundary=boundary,
    )

    lifecycle._executors.agent.ensure_available()
    lifecycle._executors.knowledge_sync.ensure_available()
    assert lifecycle._worktree_manager is not None
    assert lifecycle._verification_worktree_provider is not None
    assert lifecycle._promotion_manager is not None
    assert lifecycle._rollback_manager is not None
    assert lifecycle._trust_boundary == boundary


def test_modified_files_include_tracked_and_new_worktree_paths() -> None:
    class _Terminal:
        def execute(self, request):
            stdout = (
                "src/existing.py\n"
                if request.argv[1] == "--no-pager"
                else "src/new_module.py\n"
            )
            return CommandResult(
                argv=request.argv,
                cwd_relative=".",
                exit_code=0,
                stdout=stdout,
                stderr="",
                timed_out=False,
                cancelled=False,
                stdout_truncated=False,
                stderr_truncated=False,
            )

    assert OperationalAgentBackend._modified_files(
        _Terminal(),  # type: ignore[arg-type]
        environment_names=("PATH",),
    ) == ("src/existing.py", "src/new_module.py")
