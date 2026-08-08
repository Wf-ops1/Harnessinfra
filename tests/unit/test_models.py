"""Contratos determinísticos dos providers reais de F3.1."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import httpx
import pytest

from ai_engineering_harness.models.adapters.anthropic import AnthropicAdapter
from ai_engineering_harness.models.adapters.local import LocalAdapter
from ai_engineering_harness.models.adapters.openai import OpenAIAdapter
from ai_engineering_harness.models.provider import (
    CancellationToken,
    ProviderAuthError,
    ProviderCancelledError,
    ProviderInvalidRequestError,
    ProviderNotImplementedError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from ai_engineering_harness.models.registry import ProviderRegistry
from ai_engineering_harness.models.router import ModelRouter

_API_KEY = "sk-test123456789012345678901234567890123456"


def _responses_payload(
    *,
    content: str = "real response",
    output: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": "resp_real_123",
        "model": "server-model-2026-01-01",
        "status": "completed",
        "output": output
        if output is not None
        else [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": content}],
            }
        ],
        "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
    }


def _chat_payload(
    *,
    content: str | None = "local response",
    tool_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": "chatcmpl_local_123",
        "model": "local-server-model",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls or [],
                }
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9},
    }


def _json_response(request: httpx.Request, payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"x-request-id": "req_real_123"},
        json=payload,
        request=request,
    )


def test_openai_provider_executes_responses_http_and_preserves_real_metadata() -> None:
    observed: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers.get("authorization")
        observed["body"] = json.loads(request.content)
        return _json_response(request, _responses_payload())

    provider = OpenAIAdapter(
        model_name="requested-model",
        api_key=_API_KEY,
        base_url="https://provider.invalid/v1",
        transport=httpx.MockTransport(handler),
    )
    response = provider.complete("sentinel prompt", system_prompt="system rule")

    assert observed == {
        "url": "https://provider.invalid/v1/responses",
        "authorization": f"Bearer {_API_KEY}",
        "body": {
            "model": "requested-model",
            "input": "sentinel prompt",
            "store": False,
            "instructions": "system rule",
        },
    }
    assert response.content == "real response"
    assert response.model_name == "server-model-2026-01-01"
    assert response.request_id == "req_real_123"
    assert response.response_id == "resp_real_123"
    assert (response.prompt_tokens, response.completion_tokens, response.total_tokens) == (11, 7, 18)


def test_local_provider_uses_configurable_chat_completions_endpoint() -> None:
    observed: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers.get("authorization")
        observed["body"] = json.loads(request.content)
        return _json_response(request, _chat_payload())

    provider = LocalAdapter(
        model_name="requested-local",
        base_url="http://127.0.0.1:9999/v1/",
        transport=httpx.MockTransport(handler),
    )
    response = provider.complete("local prompt")

    assert observed == {
        "url": "http://127.0.0.1:9999/v1/chat/completions",
        "authorization": None,
        "body": {
            "model": "requested-local",
            "messages": [{"role": "user", "content": "local prompt"}],
        },
    }
    assert response.provider == "local"
    assert response.model_name == "local-server-model"
    assert response.content == "local response"


def test_tool_calls_are_sent_and_parsed_as_strict_typed_values() -> None:
    observed_body: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed_body.update(json.loads(request.content))
        return _json_response(
            request,
            _responses_payload(
                output=[
                    {
                        "type": "function_call",
                        "call_id": "call_123",
                        "name": "read_file",
                        "arguments": '{"path":"README.md"}',
                    }
                ]
            ),
        )

    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    response = provider.call_tools(
        "inspect",
        [
            {
                "name": "read_file",
                "description": "Read one file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            }
        ],
    )

    assert observed_body["tools"] == [
        {
            "type": "function",
            "name": "read_file",
            "description": "Read one file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]
    assert response.content == ""
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].call_id == "call_123"
    assert response.tool_calls[0].name == "read_file"
    assert response.tool_calls[0].arguments == {"path": "README.md"}


def test_chat_tool_schema_has_no_responses_only_nested_type() -> None:
    observed_body: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed_body.update(json.loads(request.content))
        return _json_response(
            request,
            _chat_payload(
                content=None,
                tool_calls=[
                    {
                        "id": "call_local",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"query":"x"}'},
                    }
                ],
            ),
        )

    provider = LocalAdapter(transport=httpx.MockTransport(handler))
    response = provider.call_tools(
        "search",
        [{"name": "search", "parameters": {"type": "object"}}],
    )

    assert observed_body["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "",
                "parameters": {"type": "object"},
                "strict": True,
            },
        }
    ]
    assert response.tool_calls[0].arguments == {"query": "x"}


def test_structured_output_is_requested_and_validated_locally() -> None:
    observed_body: dict[str, Any] = {}
    schema = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
        "required": ["status"],
        "additionalProperties": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        observed_body.update(json.loads(request.content))
        return _json_response(request, _responses_payload(content='{"status":"ok"}'))

    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    response = provider.structured_output("return status", schema)

    assert observed_body["text"] == {
        "format": {
            "type": "json_schema",
            "name": "harness_response",
            "strict": True,
            "schema": schema,
        }
    }
    assert response.structured_output == {"status": "ok"}


def test_invalid_structured_output_fails_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _json_response(request, _responses_payload(content='{"status":7}'))

    provider = OpenAIAdapter(
        api_key=_API_KEY,
        max_retries=3,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderResponseError, match="structured output inválido") as exc_info:
        provider.structured_output(
            "return status",
            {
                "type": "object",
                "properties": {"status": {"type": "string"}},
                "required": ["status"],
            },
        )

    assert exc_info.value.retryable is False
    assert calls == 1


def test_rate_limit_error_retries_then_returns_real_response() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": "slow down"}, request=request)
        return _json_response(request, _responses_payload())

    provider = OpenAIAdapter(
        api_key=_API_KEY,
        max_retries=1,
        backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )

    assert provider.complete("retry me").content == "real response"
    assert calls == 2


def test_rate_limit_error_is_typed_after_retry_exhaustion() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"error": "slow down"}, request=request)

    provider = OpenAIAdapter(
        api_key=_API_KEY,
        max_retries=1,
        backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderRateLimitError) as exc_info:
        provider.complete("retry me")

    assert exc_info.value.category == "rate_limit"
    assert exc_info.value.retryable is True
    assert calls == 2


def test_timeout_error_retries_only_to_configured_limit() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("transient timeout", request=request)

    provider = OpenAIAdapter(
        api_key=_API_KEY,
        max_retries=1,
        backoff_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderTimeoutError) as exc_info:
        provider.complete("retry timeout")

    assert exc_info.value.category == "timeout"
    assert calls == 2


def test_auth_error_is_redacted_and_never_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            text=f"invalid api_key={_API_KEY}",
            headers={"x-request-id": "req_auth"},
            request=request,
        )

    provider = OpenAIAdapter(
        api_key=_API_KEY,
        max_retries=3,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderAuthError) as exc_info:
        provider.complete("do not retry")

    assert exc_info.value.category == "auth"
    assert exc_info.value.request_id == "req_auth"
    assert _API_KEY not in str(exc_info.value)
    assert "REDACTED" in str(exc_info.value)
    assert calls == 1


def test_missing_remote_api_key_fails_before_transport() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _json_response(request, _responses_payload())

    provider = OpenAIAdapter(api_key=None, transport=httpx.MockTransport(handler))
    provider._api_key = None  # garante independência do ambiente do processo
    with pytest.raises(ProviderAuthError, match="credencial"):
        provider.complete("no credential")
    assert calls == 0


def test_invalid_request_error_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad input"}, request=request)

    provider = OpenAIAdapter(
        api_key=_API_KEY,
        max_retries=3,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderInvalidRequestError) as exc_info:
        provider.complete("invalid")
    assert exc_info.value.category == "invalid_request"
    assert calls == 1


def test_invalid_tool_schema_fails_before_transport() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _json_response(request, _responses_payload())

    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderInvalidRequestError, match="tool inválida"):
        provider.call_tools("tool", [{"name": "broken", "parameters": "not-a-schema"}])
    assert calls == 0


def test_invalid_tool_arguments_from_provider_fail_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(
            request,
            _responses_payload(
                output=[
                    {
                        "type": "function_call",
                        "call_id": "call_bad",
                        "name": "read_file",
                        "arguments": "[]",
                    }
                ]
            ),
        )

    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderResponseError, match="arguments"):
        provider.call_tools(
            "tool",
            [{"name": "read_file", "parameters": {"type": "object"}}],
        )


def test_missing_real_usage_fails_closed() -> None:
    payload = _responses_payload()
    del payload["usage"]

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(request, payload)

    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderResponseError, match="usage"):
        provider.complete("usage required")


def test_pre_cancelled_call_has_no_transport_effect_or_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _json_response(request, _responses_payload())

    token = CancellationToken()
    token.cancel()
    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderCancelledError):
        provider.complete("cancel", cancellation_token=token)
    assert calls == 0


def test_in_flight_cancellation_returns_without_waiting_for_transport_timeout() -> None:
    started = threading.Event()
    release = threading.Event()
    token = CancellationToken()

    def handler(request: httpx.Request) -> httpx.Response:
        started.set()
        release.wait(timeout=2)
        return _json_response(request, _responses_payload())

    def cancel_after_start() -> None:
        assert started.wait(timeout=1)
        token.cancel()

    threading.Thread(target=cancel_after_start, daemon=True).start()
    provider = OpenAIAdapter(
        api_key=_API_KEY,
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    before = time.monotonic()
    try:
        with pytest.raises(ProviderCancelledError):
            provider.complete("cancel in flight", cancellation_token=token)
    finally:
        release.set()

    assert time.monotonic() - before < 1


@pytest.mark.parametrize("operation", ["complete", "call_tools", "structured_output"])
def test_anthropic_not_implemented_never_returns_synthetic_success(operation: str) -> None:
    provider = AnthropicAdapter()
    with pytest.raises(ProviderNotImplementedError) as exc_info:
        if operation == "complete":
            provider.complete("prompt")
        elif operation == "call_tools":
            provider.call_tools("prompt", [])
        else:
            provider.structured_output("prompt", {"type": "object"})
    assert exc_info.value.category == "not_implemented"


def test_model_router_remains_compatible_with_real_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(request, _responses_payload())

    provider = OpenAIAdapter(api_key=_API_KEY, transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        ProviderRegistry,
        "get_provider",
        classmethod(lambda cls, provider_id: provider),
    )
    router = ModelRouter(allowed_providers=["openai"])
    response = router.complete_with_fallback("Test prompt", primary_provider_id="openai")
    assert response.provider == "openai"
    assert response.content == "real response"


def test_data_egress_security_violation_still_precedes_provider_creation() -> None:
    router = ModelRouter(allowed_providers=["local"])
    with pytest.raises(PermissionError, match="SECURITY VIOLATION"):
        router.complete_with_fallback(
            prompt="Sensitive code context",
            primary_provider_id="local",
            fallback_provider_ids=["openai"],
        )
