"""Provider remoto real para a OpenAI Responses API."""

from __future__ import annotations

import os

import httpx

from ai_engineering_harness.models.provider import OpenAICompatibleHTTPProvider


class OpenAIAdapter(OpenAICompatibleHTTPProvider):
    """Executa chamadas reais contra uma Responses API configurável."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.25,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            provider_id="openai",
            model_name=model_name,
            base_url=base_url or os.environ.get("HARNESS_OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_style="responses",
            api_key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY"),
            requires_api_key=True,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            transport=transport,
        )
