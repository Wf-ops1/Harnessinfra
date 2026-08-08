"""Integração live opt-in do provider remoto F3.1."""

from __future__ import annotations

import os

import pytest

from ai_engineering_harness.models.adapters.openai import OpenAIAdapter

_LIVE_ENABLED = os.environ.get("RUN_LIVE_MODEL_INTEGRATION") == "1"
_API_KEY = os.environ.get("OPENAI_API_KEY")
_MODEL = os.environ.get("HARNESS_OPENAI_TEST_MODEL")
_SKIP_REASON = (
    "requer RUN_LIVE_MODEL_INTEGRATION=1, OPENAI_API_KEY e HARNESS_OPENAI_TEST_MODEL"
)


@pytest.mark.skipif(
    not (_LIVE_ENABLED and _API_KEY and _MODEL),
    reason=_SKIP_REASON,
)
def test_openai_provider_live_returns_server_metadata_and_usage() -> None:
    provider = OpenAIAdapter(
        model_name=_MODEL or "",
        api_key=_API_KEY,
        timeout_seconds=30,
        max_retries=1,
    )
    response = provider.complete("Reply with exactly: F3.1 live provider OK")

    assert response.content
    assert response.model_name
    assert response.response_id
    assert response.request_id
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.total_tokens >= response.prompt_tokens + response.completion_tokens
