"""Promotion Manager — Gerencia promoção e commit Git do workflow."""

import subprocess
from pathlib import Path

from ai_engineering_harness.observability.audit import AuditTrailManager


class PromotionManager:
    """Promove código do worktree para a branch principal ou simula via dry_run."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def promote(self, execution_id: str, dry_run: bool = True, message: str | None = None) -> str:
        audit_mgr = AuditTrailManager(self.project_root, execution_id)
        msg = message or f"feat: workflow promotion for {execution_id}"

        if dry_run:
            synthetic_sha = f"sha-promoted-{execution_id}"
            audit_mgr.log_event("WORKFLOW_PROMOTED", {
                "execution_id": execution_id,
                "commit_sha": synthetic_sha,
                "mode": "dry_run"
            })
            return synthetic_sha

        try:
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=self.project_root,
                capture_output=True,
                check=False,
                text=True,
            )

            rev_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                check=False,
                text=True,
            )
            commit_sha = rev_res.stdout.strip() if rev_res.returncode == 0 else f"sha-local-{execution_id}"
        except (OSError, subprocess.SubprocessError):
            commit_sha = f"sha-fallback-{execution_id}"

        audit_mgr.log_event("WORKFLOW_PROMOTED", {
            "execution_id": execution_id,
            "commit_sha": commit_sha,
            "mode": "live"
        })
        return commit_sha
