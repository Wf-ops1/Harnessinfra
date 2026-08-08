"""Validação de permissões de execução de ferramentas."""



class ToolPermissions:
    """Aplica restrições da política de ferramentas (tool_policy.yaml)."""

    def __init__(self, allowed_tools: list[str] | tuple[str, ...]):
        if len(set(allowed_tools)) != len(allowed_tools):
            raise ValueError("allowed_tools contains duplicates")
        self.allowed_tools = tuple(allowed_tools)

    def is_allowed(self, tool_name: str) -> bool:
        return "*" in self.allowed_tools or tool_name in self.allowed_tools
