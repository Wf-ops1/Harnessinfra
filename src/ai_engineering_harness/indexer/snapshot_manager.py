"""Gerenciamento de snapshots do índice estrutural vinculados ao git_commit_sha."""

import json
from pathlib import Path
from typing import Any


class SnapshotManager:
    """Gerencia caches de AST salvos em .harness/state/structural-index/."""

    def __init__(self, project_root: Path):
        self.index_dir = project_root / ".harness" / "state" / "structural-index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, commit_sha: str, ast_data: dict[str, Any]) -> Path:
        snapshot_file = self.index_dir / f"snapshot_{commit_sha}.json"
        snapshot_file.write_text(json.dumps(ast_data, indent=2), encoding="utf-8")
        return snapshot_file

    def get_snapshot(self, commit_sha: str) -> dict[str, Any] | None:
        snapshot_file = self.index_dir / f"snapshot_{commit_sha}.json"
        if snapshot_file.is_file():
            return json.loads(snapshot_file.read_text(encoding="utf-8"))
        return None
