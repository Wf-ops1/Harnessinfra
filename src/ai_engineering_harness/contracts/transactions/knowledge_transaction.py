from datetime import datetime
from typing import Literal, List, Optional
from pydantic import BaseModel, ConfigDict, Field

SnapshotStatus = Literal["pending", "ready", "failed", "corrupted"]


class ArtifactVersionItem(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)
    type: str = Field(description="Tipo de artefato (ex: adr, spec, prd, domain_model)")
    id: str = Field(description="ID do artefato")
    version: str = Field(description="Versão semântica do artefato")


class KnowledgeTransaction(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)
    tx_id: str = Field(description="ID da transação")
    status: str = Field(description="Status da transação")
    created_at: datetime = Field(description="Timestamp de criação")
    staging_path: str = Field(description="Caminho de staging")
    artifact_ids: List[str] = Field(description="IDs dos artefatos")
    transaction_id: Optional[str] = Field(default=None, description="ID único da transação atômica")
    commit_sha: Optional[str] = Field(default=None, description="Hash do commit Git")
    snapshot_status: Optional[SnapshotStatus] = Field(default=None, description="Estado do snapshot")
    artifacts: Optional[List[ArtifactVersionItem]] = Field(default=None, description="Artefatos atualizados")
    visibility: Optional[str] = Field(default="atomic", description="Visibilidade")
    triggered_by: Optional[str] = Field(default=None, description="execution_id motivador")


class JournalState(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)
    state: str = Field(description="Estado do journal")
    tx_id: str = Field(description="ID da transação")
    timestamp: datetime = Field(description="Timestamp ISO")
