"""Gerenciador de Git Worktrees externos ao repositório do projeto."""

import json
from pathlib import Path
from typing import Dict, Any
from ai_engineering_harness.workspace.sandbox import SandboxProvider

class ExternalWorktreeManager:
    """Cria e gerencia Worktrees Git externos para isolamento de alterações."""

    def __init__(self, project_root: Path, project_id: str = "default-proj"):
        self.project_root = project_root
        self.project_id = project_id
        self.external_base_dir = SandboxProvider.get_external_worktree_base_dir(project_id)

    def create_worktree(self, execution_id: str, base_commit_sha: str) -> Path:
        """Cria o diretório do worktree externo e registra o ponteiro em .harness/state/worktree-references/."""
        worktree_path = self.external_base_dir / execution_id
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Grava apenas o ponteiro JSON em .harness/state/worktree-references/<exec_id>.json
        ref_dir = self.project_root / ".harness" / "state" / "worktree-references"
        ref_dir.mkdir(parents=True, exist_ok=True)

        ref_data: Dict[str, Any] = {
            "execution_id": execution_id,
            "worktree_path": str(worktree_path),
            "base_commit_sha": base_commit_sha,
            "project_id": self.project_id
        }

        ref_file = ref_dir / f"{execution_id}.json"
        ref_file.write_text(json.dumps(ref_data, indent=2), encoding="utf-8")

        return worktree_path
