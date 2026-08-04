"""Avaliador de Fronteira de Confiança do Repositório e Regra Universal de Aprovação."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class TrustEvaluationResult(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    is_trusted: bool
    mode: str  # "trusted" ou "restricted"
    allow_python_contracts: bool
    allow_unprompted_commands: bool
    reasons: list[str]

class TrustBoundaryEvaluator:
    """Governa permissões de execução baseadas na confiança do repositório-alvo."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

    def evaluate(self, force_untrusted: bool = False) -> TrustEvaluationResult:
        """Avalia se o repositório é confiável para execução de código local."""
        reasons = []

        if force_untrusted:
            return TrustEvaluationResult(
                is_trusted=False,
                mode="restricted",
                allow_python_contracts=False,
                allow_unprompted_commands=False,
                reasons=["Modo Restrito forçado via configuração/CLI."]
            )

        # Checar se existe arquivo de marcação .harness/trusted_repository
        trusted_marker = self.project_root / ".harness" / "trusted_repository"
        if trusted_marker.is_file():
            reasons.append("Marcador .harness/trusted_repository encontrado.")
            return TrustEvaluationResult(
                is_trusted=True,
                mode="trusted",
                allow_python_contracts=True,
                allow_unprompted_commands=True,
                reasons=reasons
            )

        # Por padrão, repositórios sem marcação explícita entram em Modo Restrito por segurança
        reasons.append("Repositório sem marcação explícita de confiança. Ativando Modo Restrito.")
        return TrustEvaluationResult(
            is_trusted=False,
            mode="restricted",
            allow_python_contracts=False,
            allow_unprompted_commands=False,
            reasons=reasons
        )

    def validate_rollback_hook(self, is_destructive: bool, is_trusted_repo: bool) -> bool:
        """Regra Universal de Aprovação: Hooks destrutivos SEMPRE exigem aprovação humana."""
        if is_destructive:
            # Hooks destrutivos JAMAIS são executados automaticamente
            return False  # Exige aprovação humana
        return is_trusted_repo
