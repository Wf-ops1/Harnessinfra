"""Testes unitários para a camada de modelos e Data Egress (TASK-1.5)."""

import pytest
from ai_engineering_harness.models.router import ModelRouter

def test_model_router_success():
    router = ModelRouter(allowed_providers=["openai", "anthropic"])
    res = router.complete_with_fallback("Test prompt", primary_provider_id="openai")
    assert res.provider == "openai"
    assert "OpenAI" in res.content

def test_data_egress_security_violation():
    # Apenas 'local' está autorizado
    router = ModelRouter(allowed_providers=["local"])

    # Tentativa de fallback para 'openai' não autorizada deve lançar PermissionError
    with pytest.raises(PermissionError) as exc_info:
        router.complete_with_fallback(
            prompt="Sensitive code context",
            primary_provider_id="local",
            fallback_provider_ids=["openai"]
        )
    assert "[SECURITY VIOLATION]" in str(exc_info.value)
