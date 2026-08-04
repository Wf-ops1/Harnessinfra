"""Módulo Workspace: Gerenciamento de Ambientes Isolados com Worktrees Externos."""

from .git_worktree import ExternalWorktreeManager
from .sandbox import SandboxProvider

__all__ = ["ExternalWorktreeManager", "SandboxProvider"]
