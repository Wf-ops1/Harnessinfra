"""Validação de permissões de execução de ferramentas."""



class PermissionChecker:
    """Valida se uma ferramenta está autorizada na política ativa."""

    def __init__(self, allowed_tools: list[str]):
        self.allowed_tools = allowed_tools

    def is_tool_allowed(self, tool_name: str) -> bool:
        return "*" in self.allowed_tools or tool_name in self.allowed_tools
