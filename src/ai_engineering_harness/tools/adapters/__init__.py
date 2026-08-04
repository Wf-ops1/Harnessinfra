"""Adaptadores concretos de ferramentas (Serena, Terminal, Git)."""

from .serena import SerenaAdapter
from .terminal import TerminalAdapter
from .git import GitAdapter

__all__ = ["SerenaAdapter", "TerminalAdapter", "GitAdapter"]
