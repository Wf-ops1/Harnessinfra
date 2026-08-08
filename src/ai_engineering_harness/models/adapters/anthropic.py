"""Provider Anthropic explicitamente indisponível até implementação própria."""

from __future__ import annotations

from typing import Any, Never

from ai_engineering_harness.models.provider import (
    BaseLLMProvider,
    CancellationToken,
    LLMResponse,
    ProviderNotImplementedError,
)


class AnthropicAdapter(BaseLLMProvider):
    """Falha tipada; nunca fabrica resposta para uma integração ausente."""

    def __init__(self, model_name: str = "claude-3-5-sonnet") -> None:
        super().__init__(provider_id="anthropic", model_name=model_name)

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> LLMResponse:
        self._not_implemented()

    def call_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system_prompt: str | None = None,
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> LLMResponse:
        self._not_implemented()

    def structured_output(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        *,
        cancellation_token: CancellationToken | None = None,
    ) -> LLMResponse:
        self._not_implemented()

    def _not_implemented(self) -> Never:
        raise ProviderNotImplementedError(
            "provider anthropic não implementado",
            provider_id=self.provider_id,
        )
