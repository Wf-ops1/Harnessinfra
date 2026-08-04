"""Motor central de avaliação de políticas de governança."""

from typing import Any

from ai_engineering_harness.governance.budget import BudgetTracker
from ai_engineering_harness.governance.permissions import PermissionChecker


class PolicyEngine:
    """Avaliador unificado de políticas em runtime."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        max_tokens = config.get("budget", {}).get("max_tokens", 100000)
        allowed_tools = config.get("tools", {}).get("allowed", ["*"])

        self.budget_tracker = BudgetTracker(max_tokens=max_tokens)
        self.permission_checker = PermissionChecker(allowed_tools=allowed_tools)

    def authorize_tool(self, tool_name: str) -> None:
        if not self.permission_checker.is_tool_allowed(tool_name):
            raise PermissionError(f"[POLICY VIOLATION] Ferramenta '{tool_name}' não autorizada.")

    def record_usage(self, token_count: int) -> None:
        self.budget_tracker.add_tokens(token_count)
