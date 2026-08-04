"""Schemas de entrada e saída dos nós do grafo."""

from typing import List, Dict
from pydantic import BaseModel, ConfigDict, Field

class ArchitectureAnalysis(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    summary: str = Field(description="Resumo da análise de arquitetura")
    invariants: List[str] = Field(description="Invariantes do sistema que devem ser mantidos")
    tech_stack: List[str] = Field(description="Componentes tecnológicos envolvidos")
    risks: List[str] = Field(description="Riscos identificados e mitigações propostas")

class CodeGenNode(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    target_files: List[str] = Field(description="Arquivos a serem criados ou modificados")
    story_id: str = Field(description="ID da história de usuário")
    acceptance_criteria: List[str] = Field(description="Lista de critérios de aceitação")

class ContextSufficiencyReport(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    score: float = Field(description="Pontuação calculada de suficiência (0.0 a 1.0)")
    threshold_required: float = Field(description="Limiar exigido pelo perfil ativo")
    is_sufficient: bool = Field(description="Booleano indicando se atingiu o limiar")
    dimensions: Dict[str, float] = Field(description="Detalhamento da pontuação por dimensão (KIs, AST, Spec)")
