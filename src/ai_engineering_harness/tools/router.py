"""Roteador central de ferramentas com verificação de permissões."""

from pathlib import Path
from typing import Any

from ai_engineering_harness.tools.adapters.serena import SerenaAdapter
from ai_engineering_harness.tools.adapters.terminal import TerminalAdapter
from ai_engineering_harness.tools.permissions import ToolPermissions


class ToolRouter:
    """Valida permissões e despacha chamadas de ferramentas."""

    def __init__(self, allowed_tools: list[str]):
        self.permissions = ToolPermissions(allowed_tools=allowed_tools)

    def dispatch(self, tool_name: str, payload: dict[str, Any]) -> Any:
        if not self.permissions.is_allowed(tool_name):
            raise PermissionError(f"[POLICY VIOLATION] Ferramenta '{tool_name}' não autorizada.")

        if tool_name == "serena_edit":
            serena = SerenaAdapter()
            file_p = Path(payload["file_path"]) if isinstance(payload["file_path"], str) else payload["file_path"]
            return serena.edit_file_semantic(file_p, payload.get("changes", {}))

        if tool_name == "terminal_run":
            return TerminalAdapter.run_command(payload["command"], payload["cwd"])

        raise ValueError(f"Ferramenta desconhecida: {tool_name}")
