"""Módulo Indexer: Governança de Inteligência Estrutural com Codebase-Memory MCP."""

from .codebase_memory_adapter import CodebaseMemoryAdapter
from .snapshot_manager import SnapshotManager
from .lease_manager import LeaseManager

__all__ = ["CodebaseMemoryAdapter", "SnapshotManager", "LeaseManager"]
