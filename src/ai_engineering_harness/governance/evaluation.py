"""Context Sufficiency Evaluator (Avaliador de Suficiência de Contexto)."""


from ai_engineering_harness.contracts.nodes import ContextSufficiencyReport


class ContextSufficiencyEvaluator:
    """Calcula a pontuação de suficiência de contexto e compara com o limiar do perfil."""

    @classmethod
    def evaluate(
        cls,
        dimensions: dict[str, float],
        required_threshold: float = 0.72
    ) -> ContextSufficiencyReport:
        """Calcula a média ponderada das dimensões (KIs, AST, Requisitos)."""
        if not dimensions:
            score = 0.0
        else:
            score = sum(dimensions.values()) / len(dimensions)

        score = round(score, 2)
        is_sufficient = score >= required_threshold

        return ContextSufficiencyReport(
            score=score,
            threshold_required=required_threshold,
            is_sufficient=is_sufficient,
            dimensions=dimensions
        )
