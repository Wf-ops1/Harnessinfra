"""Módulo Indexer: Governança de Inteligência Estrutural com Codebase-Memory MCP."""

from .codebase_memory_adapter import CodebaseMemoryAdapter
from .lease_manager import LeaseManager
from .snapshot_manager import SnapshotManager

__all__ = ["CodebaseMemoryAdapter", "LeaseManager", "SnapshotManager"]
