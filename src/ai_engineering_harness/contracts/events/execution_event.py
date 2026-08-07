"""Schemas de eventos de execução e sincronização de conhecimento."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    event_id: str = Field(description="Identificador único do evento")
    execution_id: str = Field(description="ID da execução vinculada")
    event_type: str = Field(description="Tipo de evento (ex: STEP_STARTED, STEP_COMPLETED)")
    timestamp: datetime = Field(description="Timestamp ISO do evento")
    payload: dict[str, Any] = Field(default_factory=dict, description="Dados específicos do evento")
    previous_hash: str | None = Field(default=None, description="SHA-256 do evento anterior no Hash Chain")
    current_hash: str | None = Field(default=None, description="SHA-256 deste evento encadeado")

class KnowledgeSyncEvent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    tx_id: str = Field(description="ID da transação de conhecimento")
    status: str = Field(description="Status da transação (STAGING, PREPARED, COMMITTED)")
    synced_at: datetime = Field(description="Timestamp do sync")
    ki_count: int = Field(description="Quantidade de KIs sincronizadas")
