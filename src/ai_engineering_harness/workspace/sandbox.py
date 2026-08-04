"""Provedor de isolamento por Sistema Operacional."""

import os
import sys
from pathlib import Path


class SandboxProvider:
    """Retorna o caminho de armazenamento de worktrees externos adequado ao SO."""

    @classmethod
    def get_external_worktree_base_dir(cls, project_id: str) -> Path:
        user_home = Path.home()

        if sys.platform == "win32":
            # Windows: %LOCALAPPDATA%/ai-engineering-harness/worktrees/<project_id>/
            local_appdata = Path(os.environ.get("LOCALAPPDATA", str(user_home / "AppData" / "Local")))
            base_path = local_appdata / "ai-engineering-harness" / "worktrees" / project_id
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/ai-engineering-harness/worktrees/<project_id>/
            base_path = user_home / "Library" / "Application Support" / "ai-engineering-harness" / "worktrees" / project_id
        else:
            # Linux: ~/.local/share/ai-engineering-harness/worktrees/<project_id>/
            base_path = user_home / ".local" / "share" / "ai-engineering-harness" / "worktrees" / project_id

        base_path.mkdir(parents=True, exist_ok=True)
        return base_path
