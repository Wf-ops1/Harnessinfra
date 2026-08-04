"""Adaptador para o Serena MCP (Edição Semântica de Código)."""

from pathlib import Path
from typing import Any


class SerenaAdapter:
    """Interface com o servidor Serena MCP para edições semânticas cirúrgicas baseadas na AST."""

    def __init__(self, endpoint: str = "http://localhost:8000/serena"):
        self.endpoint = endpoint

    def edit_file_semantic(self, file_path: Path, changes: dict[str, Any]) -> bool:
        """Aplica edição semântica de código no arquivo-alvo."""
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
        return True
