"""Focused F3.3 tests for the compiled-policy model tool loop."""

from __future__ import annotations

from typing import Any

import pytest

from ai_engineering_harness.contracts import (
    CompiledGraphArtifact,
    ContractRegistry,
    GraphSpec,
    PolicyRegistry,
    SourceManifestEntry,
)
from ai_engineering_harness.governance import BudgetTracker
from ai_engineering_harness.models import (
    CancellationToken,
    LLMResponse,
    ModelRouter,
    ProviderTimeoutError,
    ToolCall,
)
from ai_engineering_harness.runtime import (
    EffectiveToolPolicy,
    ToolLoopCancelledError,
    ToolLoopError,
    ToolLoopExecutionError,
    ToolLoopExecutor,
    ToolPolicyConfigurationError,
    ToolStepLimitExceededError,
)
from ai_engineering_harness.runtime.agent_executor import AgentExecutor
from ai_engineering_harness.tools import (
    ToolDefinition,
    ToolRegistration,
    ToolRouter,
    ToolUnavailableError,
)

_CONTRACT = "ai_engineering_harness.contracts.nodes.context_sufficiency.RetrievalRequest"


class _ToolProvider:
    def __init__(self, provider_id: str, outcomes: list[LLMResponse | Exception]) -> None:
        self.provider_id = provider_id
        self.outcomes = outcomes
        self.prompts: list[str] = []
        self.schemas: list[list[dict[str, Any]]] = []

    def call_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        **_: object,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        self.schemas.append(tools)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _Registry:
    def __init__(self, providers: dict[str, _ToolProvider]) -> None:
        self.providers = providers
        self.created: list[str] = []

    def is_configured(self, provider_id: str) -> bool:
        return provider_id in self.providers

    def create_provider(self, provider_id: str) -> _ToolProvider:
        self.created.append(provider_id)
        return self.providers[provider_id]


def _response(
    *,
    provider: str = "local",
    content: str = "",
    calls: tuple[ToolCall, ...] = (),
    total_tokens: int = 3,
    index: int = 1,
) -> LLMResponse:
    return LLMResponse(
        content=content,
        provider=provider,
        model_name=f"{provider}-model",
        tool_calls=calls,
        prompt_tokens=2,
        completion_tokens=1,
        total_tokens=total_tokens,
        request_id=f"req-{index}",
        response_id=f"resp-{index}",
    )


def _call(
    *,
    call_id: str = "call-1",
    name: str = "knowledge_retriever",
    query: object = "routing",
) -> ToolCall:
    return ToolCall(call_id=call_id, name=name, arguments={"query": query})


def _artifact(*, allow_tool: bool = True) -> CompiledGraphArtifact:
    graph = GraphSpec.model_validate(
        {
            "graph": {
                "name": "tool-loop",
                "graph_schema_version": "1.0",
                "definition_version": "3.2.0",
                "entrypoint": "agent",
                "status": "stable",
            },
            "policies": ["policies/tool_policy.yaml"],
            "nodes": [
                {
                    "id": "agent",
                    "type": "agent",
                    "role": "requirement_analyst",
                    "input_contract": _CONTRACT,
                    "output_contract": _CONTRACT,
                    "tool_permissions": (
                        [{"tool": "knowledge_retriever", "effect": "allow"}]
                        if allow_tool
                        else []
                    ),
                    "on_success": "completed",
                    "on_failure": "failed",
                }
            ],
            "terminal_states": [
                {"id": "completed", "outcome": "success"},
                {"id": "failed", "outcome": "failure"},
            ],
        }
    )
    return CompiledGraphArtifact.build(
        graph=graph,
        resolved_contracts=ContractRegistry().resolve_many([_CONTRACT]),
        resolved_policies=PolicyRegistry().resolve_graph(graph),
        source_manifest=(
            SourceManifestEntry(
                source_kind="graph",
                source_id="project://tool-loop.yaml",
                content_digest=f"sha256:{'0' * 64}",
            ),
        ),
    )


def _tool_router(handler) -> ToolRouter:
    definition = ToolDefinition(
        name="knowledge_retriever",
        description="Retrieve deterministic test knowledge.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    return ToolRouter(
        allowed_tools=("knowledge_retriever",),
        registrations={
            "knowledge_retriever": ToolRegistration(
                definition=definition,
                handler=handler,
            )
        },
    )


def _loop(
    provider: _ToolProvider,
    tool_router: ToolRouter,
    *,
    max_steps: int = 3,
    budget: BudgetTracker | None = None,
) -> tuple[ToolLoopExecutor, ModelRouter]:
    registry = _Registry({"local": provider})
    router = ModelRouter(
        allowed_providers=("local",),
        provider_registry=registry,  # type: ignore[arg-type]
        budget_tracker=budget,
        default_primary_provider="local",
    )
    return (
        ToolLoopExecutor(router, tool_router, max_tool_steps=max_steps),
        router,
    )


def _execute(loop: ToolLoopExecutor, tool_router: ToolRouter, **kwargs):
    policy = EffectiveToolPolicy.from_artifact(_artifact(), "agent")
    return loop.execute(
        "system and user prompt",
        policy=policy,
        tool_schemas=tool_router.prepare(policy.allowed_tools),
        model_candidates=("local",),
        **kwargs,
    )


def test_compiled_policy_tool_result_returns_to_model_and_final_response_stops() -> None:
    effects: list[dict[str, object]] = []

    def handler(payload):
        effects.append(payload)
        return {"matches": ["F3.3"]}

    tool_router = _tool_router(handler)
    provider = _ToolProvider(
        "local",
        [
            _response(calls=(_call(),), index=1),
            _response(content="final answer", index=2),
        ],
    )
    loop, router = _loop(provider, tool_router)

    result = _execute(loop, tool_router)

    assert effects == [{"query": "routing"}]
    assert result.final_response.content == "final answer"
    assert result.model_calls == 2
    assert result.model_call.response_id == "resp-2"
    assert router.budget_tracker.consumed_tokens == 6
    assert provider.schemas[0][0]["name"] == "knowledge_retriever"
    assert "<tool_loop_transcript>" in provider.prompts[1]
    assert '"matches":["F3.3"]' in provider.prompts[1]
    assert result.tool_executions[0].arguments_digest.startswith("sha256:")
    assert result.tool_executions[0].redacted_result == '{"matches":["F3.3"]}'


def test_transient_model_failure_falls_back_within_one_tool_turn() -> None:
    primary = _ToolProvider(
        "openai",
        [ProviderTimeoutError("timeout", provider_id="openai")],
    )
    fallback = _ToolProvider("local", [_response(content="done")])
    registry = _Registry({"openai": primary, "local": fallback})
    router = ModelRouter(
        allowed_providers=("openai", "local"),
        provider_registry=registry,  # type: ignore[arg-type]
        default_primary_provider="openai",
        default_fallback_providers=("local",),
    )
    tool_router = _tool_router(lambda payload: payload)
    loop = ToolLoopExecutor(router, tool_router, max_tool_steps=1)
    policy = EffectiveToolPolicy.from_artifact(_artifact(), "agent")

    result = loop.execute(
        "prompt",
        policy=policy,
        tool_schemas=tool_router.prepare(policy.allowed_tools),
        model_candidates=("openai", "local"),
    )

    assert result.final_response.provider == "local"
    assert registry.created == ["openai", "local"]


@pytest.mark.parametrize(
    "calls",
    [
        (_call(name="terminal_executor"),),
        (_call(query=7),),
        (_call(call_id="same"), _call(call_id="same")),
    ],
)
def test_unauthorized_schema_or_duplicate_batch_has_zero_effect(calls) -> None:
    effects: list[object] = []
    tool_router = _tool_router(lambda payload: effects.append(payload))
    provider = _ToolProvider("local", [_response(calls=calls)])
    loop, _ = _loop(provider, tool_router)

    with pytest.raises(ToolLoopError):
        _execute(loop, tool_router)

    assert effects == []
    assert len(provider.prompts) == 1


def test_unregistered_compiled_capability_fails_before_model_call() -> None:
    provider = _ToolProvider("local", [_response(content="must not run")])
    empty_router = ToolRouter(allowed_tools=("knowledge_retriever",), registrations={})
    _loop(provider, empty_router)
    policy = EffectiveToolPolicy.from_artifact(_artifact(), "agent")

    with pytest.raises(ToolUnavailableError):
        empty_router.prepare(policy.allowed_tools)

    assert provider.prompts == []


def test_agent_preflight_rejects_unregistered_tool_before_composing_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _ToolProvider("local", [_response(content="must not run")])
    registry = _Registry({"local": provider})
    model_router = ModelRouter(
        allowed_providers=("local",),
        provider_registry=registry,  # type: ignore[arg-type]
    )
    empty_router = ToolRouter(allowed_tools=("knowledge_retriever",), registrations={})
    executor = AgentExecutor("Sally", model_router, tool_router=empty_router)
    composed = False

    def compose(_: str) -> str:
        nonlocal composed
        composed = True
        return "must-not-compose"

    monkeypatch.setattr(executor, "_compose_prompt", compose)

    with pytest.raises(ToolUnavailableError):
        executor.execute_tool_loop(
            "sensitive",
            artifact=_artifact(),
            node_id="agent",
            max_tool_steps=1,
        )

    assert composed is False
    assert provider.prompts == []


def test_limit_rejects_whole_batch_before_first_effect() -> None:
    effects: list[object] = []
    tool_router = _tool_router(lambda payload: effects.append(payload))
    provider = _ToolProvider(
        "local",
        [_response(calls=(_call(call_id="one"), _call(call_id="two")))],
    )
    loop, _ = _loop(provider, tool_router, max_steps=1)

    with pytest.raises(ToolStepLimitExceededError):
        _execute(loop, tool_router)

    assert effects == []


def test_budget_exhaustion_after_model_response_blocks_tool_effect() -> None:
    effects: list[object] = []
    tool_router = _tool_router(lambda payload: effects.append(payload))
    provider = _ToolProvider("local", [_response(calls=(_call(),), total_tokens=3)])
    loop, _ = _loop(provider, tool_router, budget=BudgetTracker(max_tokens=3))

    with pytest.raises(RuntimeError, match="BUDGET EXCEEDED"):
        _execute(loop, tool_router)

    assert effects == []


def test_cancel_before_first_model_call_has_no_effect() -> None:
    effects: list[object] = []
    tool_router = _tool_router(lambda payload: effects.append(payload))
    provider = _ToolProvider("local", [_response(content="must not run")])
    loop, _ = _loop(provider, tool_router)
    token = CancellationToken()
    token.cancel()

    with pytest.raises(ToolLoopCancelledError):
        _execute(loop, tool_router, cancellation_token=token)

    assert provider.prompts == []
    assert effects == []


def test_tool_error_stops_without_another_model_call_and_carries_failed_record() -> None:
    def fail(_: object) -> object:
        raise OSError("token=must-not-persist")

    tool_router = _tool_router(fail)
    provider = _ToolProvider("local", [_response(calls=(_call(),))])
    loop, _ = _loop(provider, tool_router)

    with pytest.raises(ToolLoopExecutionError) as captured:
        _execute(loop, tool_router)

    assert len(provider.prompts) == 1
    assert len(captured.value.tool_executions) == 1
    record = captured.value.tool_executions[0]
    assert record.succeeded is False
    assert record.error_code == "ToolExecutionError"
    assert "must-not-persist" not in record.redacted_result


def test_policy_extraction_rejects_non_agent_or_missing_decision() -> None:
    with pytest.raises(ToolPolicyConfigurationError):
        EffectiveToolPolicy.from_artifact(_artifact(), "missing")

    denied = EffectiveToolPolicy.from_artifact(_artifact(allow_tool=False), "agent")
    assert denied.allowed_tools == ()
