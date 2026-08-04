"""Validação de permissões de execução de ferramentas."""

from typing import List

class ToolPermissions:
    """Aplica restrições da política de ferramentas (tool_policy.yaml)."""

    def __init__(self, allowed_tools: List[str]):
        self.allowed_tools = allowed_tools

    def is_allowed(self, tool_name: str) -> bool:
        return "*" in self.allowed_tools or tool_name in self.allowed_tools
