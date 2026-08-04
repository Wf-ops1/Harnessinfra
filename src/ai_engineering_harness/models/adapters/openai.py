"""Adaptador para provedor OpenAI."""

from typing import Any

from ai_engineering_harness.models.provider import BaseLLMProvider, LLMResponse


class OpenAIAdapter(BaseLLMProvider):
    def __init__(self, model_name: str = "gpt-4o"):
        super().__init__(provider_id="openai", model_name=model_name)

    def complete(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        content = f"[OpenAI {self.model_name}] Response to: {prompt[:30]}..."
        return LLMResponse(
            content=content,
            provider=self.provider_id,
            model_name=self.model_name,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )

    def call_tools(self, prompt: str, tools: list[dict[str, Any]], system_prompt: str | None = None) -> LLMResponse:
        return LLMResponse(
            content="Tool invocation",
            provider=self.provider_id,
            model_name=self.model_name,
            tool_calls=[{"name": tools[0]["name"] if tools else "default_tool", "args": {}}]
        )

    def structured_output(self, prompt: str, response_schema: dict[str, Any]) -> LLMResponse:
        return LLMResponse(
            content='{"status": "ok"}',
            provider=self.provider_id,
            model_name=self.model_name
        )
