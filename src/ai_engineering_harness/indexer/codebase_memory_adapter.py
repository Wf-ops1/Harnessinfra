"""Adaptador único de comunicação com o Codebase-Memory MCP."""

from pathlib import Path
from typing import Any

from ai_engineering_harness.indexer.snapshot_manager import SnapshotManager


class CodebaseMemoryAdapter:
    """Interface de inteligência de código sobre a Codebase-Memory MCP."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.snapshot_manager = SnapshotManager(project_root)

    def query_ast(self, query: str, commit_sha: str) -> dict[str, Any]:
        """Consulta a árvore AST vinculada ao commit SHA."""
        snapshot = self.snapshot_manager.get_snapshot(commit_sha)
        if snapshot:
            return snapshot

        # Simulação da resposta da Codebase-Memory MCP para o commit
        mock_ast = {
            "commit_sha": commit_sha,
            "symbols": ["main", "ConfigResolver", "DoctorChecker"],
            "classes": ["ModelRouter", "PolicyEngine"]
        }
        self.snapshot_manager.save_snapshot(commit_sha, mock_ast)
        return mock_ast
