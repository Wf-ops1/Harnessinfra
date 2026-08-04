from pydantic import BaseModel, Field


class TestGenerationInput(BaseModel):
    requirement_id: str = Field(description="ID do requisito sob teste")
    modified_files: list[str] = Field(description="Lista de arquivos de código alterados")
    acceptance_criteria: list[str] = Field(description="Critérios de aceitação a validar")


class TestGenerationOutput(BaseModel):
    test_files: list[str] = Field(description="Arquivos de teste criados ou atualizados")
    test_count: int = Field(ge=0, description="Total de casos de teste gerados")
    success: bool = Field(description="Status da geração da suíte de teste")
