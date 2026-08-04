"""Schemas de entrada e saída dos nós do grafo."""


from pydantic import BaseModel, ConfigDict, Field


class ArchitectureAnalysis(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    summary: str = Field(description="Resumo da análise de arquitetura")
    invariants: list[str] = Field(description="Invariantes do sistema que devem ser mantidos")
    tech_stack: list[str] = Field(description="Componentes tecnológicos envolvidos")
    risks: list[str] = Field(description="Riscos identificados e mitigações propostas")

class CodeGenNode(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    target_files: list[str] = Field(description="Arquivos a serem criados ou modificados")
    story_id: str = Field(description="ID da história de usuário")
    acceptance_criteria: list[str] = Field(description="Lista de critérios de aceitação")

class ContextSufficiencyReport(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    score: float = Field(description="Pontuação calculada de suficiência (0.0 a 1.0)")
    threshold_required: float = Field(description="Limiar exigido pelo perfil ativo")
    is_sufficient: bool = Field(description="Booleano indicando se atingiu o limiar")
    dimensions: dict[str, float] = Field(description="Detalhamento da pontuação por dimensão (KIs, AST, Spec)")
