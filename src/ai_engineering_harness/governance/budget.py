"""Rastreamento de uso de tokens e orçamento."""

class BudgetTracker:
    """Monitora o consumo de tokens durante uma execução."""

    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.consumed_tokens = 0

    def add_tokens(self, count: int) -> None:
        self.consumed_tokens += count
        if self.consumed_tokens > self.max_tokens:
            raise RuntimeError(
                f"[BUDGET EXCEEDED] Orçamento máximo de tokens excedido: {self.consumed_tokens} > {self.max_tokens}"
            )
