"""Adaptadores concretos de ferramentas (Serena, Terminal, Git)."""

from .git import GitAdapter
from .serena import SerenaAdapter
from .terminal import TerminalAdapter

__all__ = ["GitAdapter", "SerenaAdapter", "TerminalAdapter"]
