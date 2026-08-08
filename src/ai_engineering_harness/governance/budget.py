"""Rastreamento estrito de uso de tokens e orçamento."""


class BudgetError(RuntimeError):
    """Base para falhas públicas do orçamento de tokens."""


class BudgetExceededError(BudgetError):
    """O orçamento foi consumido ou ultrapassado."""

    def __init__(self, *, max_tokens: int, consumed_tokens: int) -> None:
        super().__init__(
            "[BUDGET EXCEEDED] Orçamento máximo de tokens excedido ou esgotado: "
            f"{consumed_tokens} >= {max_tokens}"
        )
        self.max_tokens = max_tokens
        self.consumed_tokens = consumed_tokens


class BudgetTracker:
    """Monitora usage real e bloqueia antes do próximo efeito após esgotamento."""

    def __init__(self, max_tokens: int = 100_000) -> None:
        if type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("max_tokens deve ser um inteiro positivo")
        self.max_tokens = max_tokens
        self.consumed_tokens = 0

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.consumed_tokens)

    @property
    def is_exhausted(self) -> bool:
        return self.consumed_tokens >= self.max_tokens

    def ensure_available(self) -> None:
        """Falha antes de uma nova chamada quando não há orçamento disponível."""
        if self.is_exhausted:
            raise BudgetExceededError(
                max_tokens=self.max_tokens,
                consumed_tokens=self.consumed_tokens,
            )

    def add_tokens(self, count: int) -> None:
        """Registra a contagem real da resposta e falha se ela ultrapassou o teto."""
        if type(count) is not int or count < 0:
            raise ValueError("token count deve ser um inteiro não negativo")
        self.consumed_tokens += count
        if self.consumed_tokens > self.max_tokens:
            raise BudgetExceededError(
                max_tokens=self.max_tokens,
                consumed_tokens=self.consumed_tokens,
            )
