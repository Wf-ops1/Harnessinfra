"""Catálogo de adaptadores de provedores configurados."""

from typing import Dict, Type
from ai_engineering_harness.models.provider import BaseLLMProvider
from ai_engineering_harness.models.adapters.openai import OpenAIAdapter
from ai_engineering_harness.models.adapters.anthropic import AnthropicAdapter
from ai_engineering_harness.models.adapters.local import LocalAdapter

class ProviderRegistry:
    """Registro estático e fábrica de adaptadores de provedores."""

    _registry: Dict[str, Type[BaseLLMProvider]] = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "local": LocalAdapter,
    }

    @classmethod
    def get_provider(cls, provider_id: str) -> BaseLLMProvider:
        if provider_id not in cls._registry:
            raise ValueError(f"Provedor não registrado: {provider_id}")
        return cls._registry[provider_id]()
