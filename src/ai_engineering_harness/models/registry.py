"""Catálogo de adaptadores de provedores configurados."""

from collections.abc import Callable
from typing import ClassVar

from ai_engineering_harness.models.adapters.anthropic import AnthropicAdapter
from ai_engineering_harness.models.adapters.local import LocalAdapter
from ai_engineering_harness.models.adapters.openai import OpenAIAdapter
from ai_engineering_harness.models.provider import BaseLLMProvider


class ProviderRegistry:
    """Registro estático e fábrica de adaptadores de provedores."""

    _registry: ClassVar[dict[str, Callable[[], BaseLLMProvider]]] = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "local": LocalAdapter,
    }

    @classmethod
    def get_provider(cls, provider_id: str) -> BaseLLMProvider:
        if provider_id not in cls._registry:
            raise ValueError(f"Provedor não registrado: {provider_id}")
        return cls._registry[provider_id]()
