from typing import Literal
from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    requirement_id: str = Field(description="ID do requisito ou funcionalidade solicitada")
    graph_type: Literal["new_feature", "bug_fix", "refactoring", "migration", "incident"] = Field(
        description="Tipo de grafo em execução"
    )
    query: str = Field(description="Consulta em linguagem natural para o Knowledge Plane")


class ContextSufficiencyReport(BaseModel):
    is_sufficient: bool = Field(description="Indica se o contexto recuperado atende os critérios do Dual-Gate")
    confidence: float = Field(ge=0.0, le=1.0, description="Nível de confiança semântica (mínimo 0.72)")
    coverage_map: dict[str, bool] = Field(description="Mapeamento de presença dos artefatos obrigatórios")
    missing_items: list[str] = Field(default_factory=list, description="Lista de artefatos ausentes")
    ambiguities: list[str] = Field(default_factory=list, description="Lista de contradições ou ambiguidades")
    recommended_action: Literal["proceed", "retrieve_more", "request_human", "abort"] = Field(
        description="Ação recomendada ao roteador condicional"
    )
    retry_count: int = Field(default=0, description="Número de retentativas de recuperação realizadas")
