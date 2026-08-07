"""Schemas de eventos de execução e sincronização de conhecimento."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from ..execution import ExecutionId

EXECUTION_EVENT_SCHEMA_VERSION = "1.0"

_NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ExecutionEvent(BaseModel):
    """Strict JSON-native envelope used by the canonical F2.2 journal."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    event_schema_version: Annotated[
        str,
        StringConstraints(pattern=r"^1\.0$"),
    ] = EXECUTION_EVENT_SCHEMA_VERSION
    event_id: ExecutionId = Field(description="Identificador único do evento")
    execution_id: ExecutionId = Field(description="ID da execução vinculada")
    event_type: _NonEmptyStr = Field(
        description="Tipo de evento (ex: STEP_STARTED, STEP_COMPLETED)"
    )
    timestamp: datetime = Field(description="Timestamp ISO do evento")
    payload: dict[str, Any] = Field(default_factory=dict, description="Dados específicos do evento")
    previous_hash: _NonEmptyStr | None = Field(
        default=None,
        description="SHA-256 do evento anterior no Hash Chain",
    )
    current_hash: _NonEmptyStr | None = Field(
        default=None,
        description="SHA-256 deste evento encadeado",
    )

    @field_validator("timestamp")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event timestamp must be timezone-aware UTC")
        if value.utcoffset() != timedelta(0):
            raise ValueError("event timestamp must use UTC")
        return value.astimezone(UTC)

    @field_validator("payload", mode="before")
    @classmethod
    def require_json_native_payload(cls, value: object) -> object:
        copied = _copy_json_native(value, path="payload")
        if not isinstance(copied, dict):
            raise TypeError("event payload must be a JSON object")
        return copied

    def canonical_json(self) -> str:
        """Serialize the envelope as one compact canonical journal line."""
        try:
            serialized = json.dumps(
                self.model_dump(mode="json"),
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"event cannot be serialized as canonical JSON: {exc}") from exc
        return serialized + "\n"


def _copy_json_native(value: object, *, path: str) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value
    if type(value) is list:
        return [
            _copy_json_native(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        copied: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path} contains a non-string object key")
            copied[key] = _copy_json_native(item, path=f"{path}.{key}")
        return copied
    raise ValueError(f"{path} contains non-JSON-native value {type(value).__name__}")

class KnowledgeSyncEvent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    tx_id: str = Field(description="ID da transação de conhecimento")
    status: str = Field(description="Status da transação (STAGING, PREPARED, COMMITTED)")
    synced_at: datetime = Field(description="Timestamp do sync")
    ki_count: int = Field(description="Quantidade de KIs sincronizadas")
