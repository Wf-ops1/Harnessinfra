"""Roteador inteligente de LLMs com controle de Data Egress e Fallback Seguro."""

import time

from ai_engineering_harness.models.provider import LLMResponse
from ai_engineering_harness.models.registry import ProviderRegistry


class ModelRouter:
    """Roteador com checagem de Data Egress e política de Fallback."""

    def __init__(self, allowed_providers: list[str]):
        self.allowed_providers = allowed_providers

    def _validate_egress(self, provider_id: str) -> None:
        """Verifica se o provedor está autorizado pelas regras de data egress."""
        if provider_id not in self.allowed_providers:
            raise PermissionError(
                f"[SECURITY VIOLATION] Provedor '{provider_id}' não está autorizado na política de data egress: {self.allowed_providers}"
            )

    def complete_with_fallback(
        self,
        prompt: str,
        primary_provider_id: str,
        fallback_provider_ids: list[str] | None = None,
        max_retries: int = 2
    ) -> LLMResponse:
        """Executa a conclusão no provedor primário com fallback seguro."""
        candidates = [primary_provider_id] + (fallback_provider_ids or [])

        # Validação estrita de Data Egress de TODOS os candidatos ANTES de iniciar qualquer execução
        for provider_id in candidates:
            self._validate_egress(provider_id)

        last_error = None
        for provider_id in candidates:
            provider = ProviderRegistry.get_provider(provider_id)

            for attempt in range(max_retries + 1):
                try:
                    return provider.complete(prompt)
                except (OSError, RuntimeError, TimeoutError, TypeError, ValueError) as e:
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(0.1 * (2 ** attempt))  # Exponential backoff

        raise RuntimeError(f"Todos os provedores de modelo falharam: {last_error}")
