"""Executor de personas de agentes conectados ao Models Router e Tool Router."""

from pathlib import Path
from typing import Dict, Any, Optional
from ai_engineering_harness.models.router import ModelRouter
from ai_engineering_harness.models.provider import LLMResponse
from ai_engineering_harness.tools.router import ToolRouter


class AgentExecutor:
    """Executa o raciocínio da persona atribuída ao nó (Winston, Amelia, etc.) e interage via ToolRouter."""

    def __init__(self, agent_name: str, router: ModelRouter, tool_router: Optional[ToolRouter] = None, project_root: Optional[Path] = None):
        self.agent_name = agent_name
        self.router = router
        self.tool_router = tool_router
        self.project_root = project_root
        self.system_prompt = self._load_agent_system_prompt()

    def _load_agent_system_prompt(self) -> str:
        role_map = {
            "Winston": "architecture_analyst",
            "Amelia": "code_agent",
            "Sally": "requirement_analyst",
            "Paige": "knowledge_updater",
            "Test": "test_agent",
            "Security": "security_agent"
        }
        role_folder = role_map.get(self.agent_name, self.agent_name.lower())

        if self.project_root:
            candidates = [
                self.project_root / "src" / "ai_engineering_harness" / "defaults" / "agents" / role_folder / "system_prompt.md",
                self.project_root / ".harness" / "agents" / role_folder / "system_prompt.md",
            ]
            for c in candidates:
                if c.exists():
                    return c.read_text(encoding="utf-8")

        return f"Você é {self.agent_name}, executando uma etapa do grafo agentic do BMad Method."

    def execute_node(self, prompt: str, primary_provider: str = "local") -> LLMResponse:
        full_prompt = f"{self.system_prompt}\n\n{prompt}"
        return self.router.complete_with_fallback(
            prompt=full_prompt,
            primary_provider_id=primary_provider
        )

    def execute_tool(self, tool_name: str, payload: Dict[str, Any]) -> Any:
        if not self.tool_router:
            raise PermissionError(f"[POLICY ERROR] Nenhum ToolRouter associado ao executor do agente '{self.agent_name}'.")
        return self.tool_router.dispatch(tool_name, payload)
