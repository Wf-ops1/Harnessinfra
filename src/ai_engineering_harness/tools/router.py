"""Fail-closed operational tool registry and policy-scoped dispatch."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import BaseModel, ConfigDict, JsonValue, StringConstraints, field_validator

from ai_engineering_harness.models.provider import ToolCall
from ai_engineering_harness.security.redaction import Redactor
from ai_engineering_harness.tools.permissions import ToolPermissions

_NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ToolHandler = Callable[[dict[str, JsonValue]], JsonValue]


class ToolRouterError(RuntimeError):
    """Base class for public operational tool routing failures."""


class ToolUnauthorizedError(PermissionError, ToolRouterError):
    """The effective compiled policy does not authorize a tool."""


class ToolUnavailableError(ToolRouterError):
    """A declared capability has no explicitly registered operational handler."""


class ToolPayloadValidationError(ToolRouterError):
    """A model-supplied tool payload violates its registered schema."""


class ToolExecutionError(ToolRouterError):
    """An operational tool handler failed without exposing its raw exception."""


class ToolDefinition(BaseModel):
    """Provider-facing schema for one operational tool."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    name: _NonEmptyStr
    description: _NonEmptyStr
    parameters: dict[str, JsonValue]

    @field_validator("parameters")
    @classmethod
    def require_valid_json_schema(
        cls,
        value: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        try:
            Draft202012Validator.check_schema(value)
        except SchemaError as exc:
            raise ValueError(f"invalid tool JSON Schema: {exc.message}") from exc
        return value

    def provider_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    """One explicit operational handler and its immutable public definition."""

    definition: ToolDefinition
    handler: ToolHandler


class ToolRouter:
    """Validate a compiled allowlist and dispatch only operational registrations."""

    def __init__(
        self,
        allowed_tools: list[str] | tuple[str, ...],
        *,
        registrations: Mapping[str, ToolRegistration] | None = None,
    ) -> None:
        self.permissions = ToolPermissions(allowed_tools=allowed_tools)
        source = registrations if registrations is not None else {}
        copied: dict[str, ToolRegistration] = {}
        for name, registration in source.items():
            if name != registration.definition.name:
                raise ValueError("tool registration key must match its definition name")
            if name in copied:
                raise ValueError(f"duplicate tool registration: {name}")
            copied[name] = registration
        self._registrations = copied

    @property
    def registered_tools(self) -> tuple[str, ...]:
        return tuple(sorted(self._registrations))

    def prepare(
        self,
        effective_allowed_tools: Sequence[str],
        *,
        effective_denied_tools: Sequence[str] = (),
    ) -> tuple[dict[str, Any], ...]:
        """Validate an exact compiled allowlist before prompt composition."""
        allowed, denied = self._validate_effective_policy(
            effective_allowed_tools,
            effective_denied_tools,
        )
        schemas: list[dict[str, Any]] = []
        for name in allowed:
            self._require_authorized(name, allowed, denied)
            registration = self._registration(name)
            schemas.append(registration.definition.provider_schema())
        return tuple(schemas)

    def validate_calls(
        self,
        calls: Sequence[ToolCall],
        effective_allowed_tools: Sequence[str],
        *,
        effective_denied_tools: Sequence[str] = (),
    ) -> None:
        """Validate an entire model batch before its first effect."""
        allowed, denied = self._validate_effective_policy(
            effective_allowed_tools,
            effective_denied_tools,
        )
        seen_call_ids: set[str] = set()
        for call in calls:
            if call.call_id in seen_call_ids:
                raise ToolPayloadValidationError("tool call IDs must be unique within a batch")
            seen_call_ids.add(call.call_id)
            self._require_authorized(call.name, allowed, denied)
            registration = self._registration(call.name)
            try:
                Draft202012Validator(registration.definition.parameters).validate(
                    call.arguments
                )
            except ValidationError as exc:
                raise ToolPayloadValidationError(
                    f"tool payload violates schema for {call.name}"
                ) from exc

    def dispatch(
        self,
        tool_name: str,
        payload: dict[str, JsonValue],
        *,
        effective_allowed_tools: Sequence[str] | None = None,
        effective_denied_tools: Sequence[str] = (),
    ) -> JsonValue:
        candidate_allowed = (
            tuple(effective_allowed_tools)
            if effective_allowed_tools is not None
            else tuple(self.permissions.allowed_tools)
        )
        allowed, denied = self._validate_effective_policy(
            candidate_allowed,
            effective_denied_tools,
        )
        self._require_authorized(tool_name, allowed, denied)
        registration = self._registration(tool_name)
        try:
            Draft202012Validator(registration.definition.parameters).validate(payload)
        except ValidationError as exc:
            raise ToolPayloadValidationError(
                f"tool payload violates schema for {tool_name}"
            ) from exc
        try:
            result = registration.handler(payload)
            return _copy_json_value(result)
        except ToolRouterError:
            raise
        except Exception as exc:
            safe_type = Redactor.redact_text(type(exc).__name__)
            raise ToolExecutionError(f"tool {tool_name} failed: {safe_type}") from exc

    @staticmethod
    def _validate_effective_policy(
        effective_allowed: Sequence[str],
        effective_denied: Sequence[str],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        allowed = tuple(effective_allowed)
        denied = tuple(effective_denied)
        if len(set(allowed)) != len(allowed):
            raise ToolUnauthorizedError("effective tool allowlist contains duplicates")
        if len(set(denied)) != len(denied):
            raise ToolUnauthorizedError("effective tool denylist contains duplicates")
        overlap = sorted(set(allowed) & set(denied))
        if overlap:
            raise ToolUnauthorizedError(
                "effective tool policy overlaps allow and deny: "
                + ", ".join(overlap)
            )
        return allowed, denied

    def _require_authorized(
        self,
        name: str,
        effective_allowed: Sequence[str],
        effective_denied: Sequence[str],
    ) -> None:
        if (
            name in effective_denied
            or name not in effective_allowed
            or not self.permissions.is_allowed(name)
        ):
            raise ToolUnauthorizedError(f"tool is not authorized by effective policy: {name}")

    def _registration(self, name: str) -> ToolRegistration:
        try:
            return self._registrations[name]
        except KeyError as exc:
            raise ToolUnavailableError(
                f"tool capability has no operational registration: {name}"
            ) from exc
def _copy_json_value(value: object) -> JsonValue:
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return json.loads(serialized)
    except (TypeError, ValueError) as exc:
        raise ToolExecutionError("tool result must be JSON-native") from exc


__all__ = [
    "ToolDefinition",
    "ToolExecutionError",
    "ToolPayloadValidationError",
    "ToolRegistration",
    "ToolRouter",
    "ToolRouterError",
    "ToolUnauthorizedError",
    "ToolUnavailableError",
]
