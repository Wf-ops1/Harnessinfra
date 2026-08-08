"""Camada de abstração e transporte de modelos LLM."""

from .provider import (
    BaseLLMProvider,
    CancellationToken,
    LLMResponse,
    OpenAICompatibleHTTPProvider,
    ProviderAuthError,
    ProviderCancelledError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderNotImplementedError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ToolCall,
)
from .registry import ProviderConfiguration, ProviderRegistry
from .router import (
    ModelEgressDeniedError,
    ModelRouteConfiguration,
    ModelRouter,
    ModelRoutingConfigurationError,
    ModelRoutingIntegrityError,
    ModelsConfiguration,
)

__all__ = [
    "BaseLLMProvider",
    "CancellationToken",
    "LLMResponse",
    "ModelEgressDeniedError",
    "ModelRouteConfiguration",
    "ModelRouter",
    "ModelRoutingConfigurationError",
    "ModelRoutingIntegrityError",
    "ModelsConfiguration",
    "OpenAICompatibleHTTPProvider",
    "ProviderAuthError",
    "ProviderCancelledError",
    "ProviderConfiguration",
    "ProviderError",
    "ProviderInvalidRequestError",
    "ProviderNotImplementedError",
    "ProviderRateLimitError",
    "ProviderRegistry",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "ToolCall",
]
