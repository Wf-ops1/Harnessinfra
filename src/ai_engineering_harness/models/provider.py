"""Interface base para provedores de modelos LLM."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMResponse(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    content: str
    provider: str
    model_name: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class BaseLLMProvider(ABC):
    """Interface abstrata para provedores de LLM."""

    def __init__(self, provider_id: str, model_name: str):
        self.provider_id = provider_id
        self.model_name = model_name

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        pass

    @abstractmethod
    def call_tools(self, prompt: str, tools: list[dict[str, Any]], system_prompt: str | None = None) -> LLMResponse:
        pass

    @abstractmethod
    def structured_output(self, prompt: str, response_schema: dict[str, Any]) -> LLMResponse:
        pass
