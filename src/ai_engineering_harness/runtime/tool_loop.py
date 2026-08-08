"""Policy-bound, budgeted and auditable model tool-call loop."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ai_engineering_harness.contracts import AgentNodeSpec, CompiledGraphArtifact
from ai_engineering_harness.contracts.policies import EffectiveNodeToolPolicySpec
from ai_engineering_harness.governance import BudgetError
from ai_engineering_harness.models.provider import (
    CancellationToken,
    LLMResponse,
    ModelToolConversation,
    ModelToolConversationTurn,
    ModelToolResult,
    ProviderError,
    ToolCall,
)
from ai_engineering_harness.models.router import (
    ModelEgressDeniedError,
    ModelResponseBudgetExceededError,
    ModelResponseCancelledError,
    ModelRouter,
    ModelRoutingConfigurationError,
    ModelRoutingIntegrityError,
)
from ai_engineering_harness.security.redaction import Redactor
from ai_engineering_harness.tools import ToolRouter, ToolRouterError

from .node_executors import ModelCallMetadata, ToolExecutionRecord

_TOOL_POLICY_REFERENCE = "policies/tool_policy.yaml"
_NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ToolLoopError(RuntimeError):
    """Base error carrying records already produced before a loop failure."""

    def __init__(
        self,
        message: str,
        *,
        tool_executions: tuple[ToolExecutionRecord, ...] = (),
        model_call_records: tuple[ModelCallMetadata, ...] = (),
    ) -> None:
        super().__init__(message)
        self.tool_executions = tool_executions
        self.model_call_records = model_call_records


class ToolPolicyConfigurationError(ToolLoopError):
    """The compiled artifact has no unique valid policy decision for a node."""


class ToolStepLimitExceededError(ToolLoopError):
    """A model batch exceeds the remaining configured tool-call budget."""


class ToolLoopExecutionError(ToolLoopError):
    """An operational tool failed and the model loop stopped."""


class ToolLoopCancelledError(ToolLoopError):
    """Cancellation was observed before the next model or tool effect."""


class EffectiveToolPolicy(BaseModel):
    """Exact immutable policy decision consumed by one agent node."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    node_id: _NonEmptyStr
    role: _NonEmptyStr
    allowed_tools: tuple[_NonEmptyStr, ...]
    denied_tools: tuple[_NonEmptyStr, ...]

    @classmethod
    def from_artifact(
        cls,
        artifact: CompiledGraphArtifact,
        node_id: str,
    ) -> EffectiveToolPolicy:
        nodes = [node for node in artifact.graph.nodes if node.id == node_id]
        if len(nodes) != 1 or not isinstance(nodes[0], AgentNodeSpec):
            raise ToolPolicyConfigurationError(
                "tool loop requires one compiled agent node"
            )
        node = nodes[0]
        policies = [
            policy
            for policy in artifact.resolved_policies
            if policy.requested_reference == _TOOL_POLICY_REFERENCE
        ]
        if len(policies) != 1:
            raise ToolPolicyConfigurationError(
                "compiled artifact requires one effective tool policy"
            )
        roles = policies[0].effective_policy.get("roles")
        if not isinstance(roles, dict):
            raise ToolPolicyConfigurationError("effective tool policy roles are malformed")

        candidates: list[EffectiveNodeToolPolicySpec] = []
        try:
            for role_document in roles.values():
                if not isinstance(role_document, dict):
                    raise TypeError
                decisions = role_document.get("nodes")
                if not isinstance(decisions, list):
                    raise TypeError
                for raw_decision in decisions:
                    decision = EffectiveNodeToolPolicySpec.model_validate(raw_decision)
                    if decision.node_id == node_id:
                        candidates.append(decision)
        except (TypeError, ValueError) as exc:
            raise ToolPolicyConfigurationError(
                "effective tool policy decisions are malformed"
            ) from exc
        if len(candidates) != 1 or candidates[0].role != node.role:
            raise ToolPolicyConfigurationError(
                "effective tool policy decision is absent, duplicate or role-divergent"
            )
        decision = candidates[0]
        return cls(
            node_id=decision.node_id,
            role=decision.role,
            allowed_tools=decision.allowed_tools,
            denied_tools=decision.denied_tools,
        )


class ToolLoopResult(BaseModel):
    """Successful final model response and redaction-safe tool evidence."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    final_response: LLMResponse
    model_call_records: tuple[ModelCallMetadata, ...]
    tool_executions: tuple[ToolExecutionRecord, ...]
    model_calls: int = Field(ge=1)

    @field_validator("model_call_records", "tool_executions", mode="before")
    @classmethod
    def freeze_records(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def require_complete_model_call_evidence(self) -> ToolLoopResult:
        if len(self.model_call_records) != self.model_calls:
            raise ValueError("model_calls must match model_call_records")
        if self.model_call_records[-1].response_id != self.final_response.response_id:
            raise ValueError("final response must match the last model call record")
        response_ids = tuple(record.response_id for record in self.model_call_records)
        if len(set(response_ids)) != len(response_ids):
            raise ValueError("model call response IDs must be unique")
        return self

    @property
    def model_call(self) -> ModelCallMetadata:
        """Compatibility accessor for the last completed model call."""
        return self.model_call_records[-1]


class ToolLoopExecutor:
    """Run model/tool turns until final content or a fail-closed stop condition."""

    def __init__(
        self,
        model_router: ModelRouter,
        tool_router: ToolRouter,
        *,
        max_tool_steps: int,
    ) -> None:
        if type(max_tool_steps) is not int or max_tool_steps <= 0:
            raise ValueError("max_tool_steps must be a positive integer")
        self._model_router = model_router
        self._tool_router = tool_router
        self._max_tool_steps = max_tool_steps

    def execute(
        self,
        prompt: str,
        *,
        policy: EffectiveToolPolicy,
        tool_schemas: tuple[dict[str, object], ...],
        model_candidates: tuple[str, ...],
        cancellation_token: CancellationToken | None = None,
    ) -> ToolLoopResult:
        records: list[ToolExecutionRecord] = []
        model_call_records: list[ModelCallMetadata] = []
        conversation_turns: list[ModelToolConversationTurn] = []
        seen_call_ids: set[str] = set()
        model_calls = 0

        while True:
            self._raise_if_cancelled(
                cancellation_token,
                records,
                model_call_records,
            )
            try:
                if conversation_turns:
                    response = self._model_router.continue_tools_with_fallback(
                        ModelToolConversation(
                            initial_prompt=prompt,
                            turns=tuple(conversation_turns),
                        ),
                        list(tool_schemas),
                        primary_provider_id=model_candidates[0],
                        fallback_provider_ids=model_candidates[1:],
                        cancellation_token=cancellation_token,
                    )
                else:
                    response = self._model_router.call_tools_with_fallback(
                        prompt,
                        list(tool_schemas),
                        primary_provider_id=model_candidates[0],
                        fallback_provider_ids=model_candidates[1:],
                        cancellation_token=cancellation_token,
                    )
            except ModelResponseBudgetExceededError as exc:
                model_call_records.append(ModelCallMetadata.from_response(exc.response))
                raise ToolLoopError(
                    str(exc),
                    tool_executions=tuple(records),
                    model_call_records=tuple(model_call_records),
                ) from exc
            except (ModelResponseCancelledError, ModelRoutingIntegrityError) as exc:
                model_call_records.append(ModelCallMetadata.from_response(exc.response))
                raise ToolLoopError(
                    "model tool call rejected after response",
                    tool_executions=tuple(records),
                    model_call_records=tuple(model_call_records),
                ) from exc
            except (
                ProviderError,
                BudgetError,
                ModelEgressDeniedError,
                ModelRoutingConfigurationError,
            ) as exc:
                raise ToolLoopError(
                    "model tool call failed",
                    tool_executions=tuple(records),
                    model_call_records=tuple(model_call_records),
                ) from exc
            model_calls += 1
            model_call_records.append(ModelCallMetadata.from_response(response))
            if not response.tool_calls:
                if not response.content.strip():
                    raise ToolLoopError(
                        "final model response must contain non-empty content",
                        tool_executions=tuple(records),
                        model_call_records=tuple(model_call_records),
                    )
                return ToolLoopResult(
                    final_response=response,
                    model_call_records=tuple(model_call_records),
                    tool_executions=tuple(records),
                    model_calls=model_calls,
                )

            try:
                self._model_router.budget_tracker.ensure_available()
            except BudgetError as exc:
                raise ToolLoopError(
                    str(exc),
                    tool_executions=tuple(records),
                    model_call_records=tuple(model_call_records),
                ) from exc
            self._raise_if_cancelled(
                cancellation_token,
                records,
                model_call_records,
            )
            self._validate_batch(
                response.tool_calls,
                policy,
                seen_call_ids=seen_call_ids,
                completed_steps=len(records),
                records=records,
                model_call_records=model_call_records,
            )
            tool_results: list[ModelToolResult] = []
            for call in response.tool_calls:
                self._raise_if_cancelled(
                    cancellation_token,
                    records,
                    model_call_records,
                )
                step = len(records) + 1
                arguments_json = _canonical_json(call.arguments)
                try:
                    result = self._tool_router.dispatch(
                        call.name,
                        call.arguments,
                        effective_allowed_tools=policy.allowed_tools,
                    )
                except ToolRouterError as exc:
                    error_text = Redactor.redact_text(str(exc))[:2_000]
                    record = ToolExecutionRecord(
                        step=step,
                        call_id=call.call_id,
                        tool_name=call.name,
                        arguments_digest=_digest(arguments_json),
                        succeeded=False,
                        result_digest=_digest(_canonical_json(error_text)),
                        redacted_result=error_text,
                        error_code=type(exc).__name__,
                    )
                    records.append(record)
                    raise ToolLoopExecutionError(
                        "tool execution failed",
                        tool_executions=tuple(records),
                        model_call_records=tuple(model_call_records),
                    ) from exc

                result_json = _canonical_json(result)
                records.append(
                    ToolExecutionRecord(
                        step=step,
                        call_id=call.call_id,
                        tool_name=call.name,
                        arguments_digest=_digest(arguments_json),
                        succeeded=True,
                        result_digest=_digest(result_json),
                        redacted_result=Redactor.redact_text(result_json)[:2_000],
                    )
                )
                tool_results.append(
                    ModelToolResult(
                        call_id=call.call_id,
                        name=call.name,
                        result=result,
                    )
                )
                seen_call_ids.add(call.call_id)

            conversation_turns.append(
                ModelToolConversationTurn(
                    response=response,
                    tool_results=tuple(tool_results),
                )
            )

    def _validate_batch(
        self,
        calls: tuple[ToolCall, ...],
        policy: EffectiveToolPolicy,
        *,
        seen_call_ids: set[str],
        completed_steps: int,
        records: list[ToolExecutionRecord],
        model_call_records: list[ModelCallMetadata],
    ) -> None:
        if completed_steps + len(calls) > self._max_tool_steps:
            raise ToolStepLimitExceededError(
                "tool call batch exceeds max_tool_steps",
                tool_executions=tuple(records),
                model_call_records=tuple(model_call_records),
            )
        if any(call.call_id in seen_call_ids for call in calls):
            raise ToolLoopError(
                "tool call ID was reused across model turns",
                tool_executions=tuple(records),
                model_call_records=tuple(model_call_records),
            )
        try:
            self._tool_router.validate_calls(calls, policy.allowed_tools)
        except ToolRouterError as exc:
            raise ToolLoopError(
                "tool call batch failed preflight",
                tool_executions=tuple(records),
                model_call_records=tuple(model_call_records),
            ) from exc

    @staticmethod
    def _raise_if_cancelled(
        token: CancellationToken | None,
        records: list[ToolExecutionRecord],
        model_call_records: list[ModelCallMetadata],
    ) -> None:
        if token is not None and token.is_cancelled:
            raise ToolLoopCancelledError(
                "tool loop cancelled",
                tool_executions=tuple(records),
                model_call_records=tuple(model_call_records),
            )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(canonical: str) -> str:
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "EffectiveToolPolicy",
    "ToolLoopCancelledError",
    "ToolLoopError",
    "ToolLoopExecutionError",
    "ToolLoopExecutor",
    "ToolLoopResult",
    "ToolPolicyConfigurationError",
    "ToolStepLimitExceededError",
]
