"""Testes unitários para o módulo de Segurança, Secrets e Trust (Fase 2)."""

import os
from pathlib import Path
from ai_engineering_harness.security.secrets import SecretManager
from ai_engineering_harness.security.redaction import Redactor
from ai_engineering_harness.security.trust import TrustBoundaryEvaluator

def test_secret_manager_in_memory():
    os.environ["OPENAI_API_KEY"] = "sk-test12345678901234567890123456789012"
    val = SecretManager.get_secret("OPENAI_API_KEY")
    assert val == "sk-test12345678901234567890123456789012"
    
    # Limpar após o teste
    del os.environ["OPENAI_API_KEY"]

def test_redactor_sanitizes_openai_key():
    text = "Erro na chamada com a chave sk-abc12345678901234567890123456789012 no payload."
    redacted = Redactor.redact_text(text)
    assert "sk-abc" not in redacted
    assert "[REDACTED_SECRET]" in redacted

def test_redactor_dynamic_secrets():
    secrets = {"MY_TOKEN": "secret_token_val_123"}
    text = "Conectando usando secret_token_val_123 no endpoint."
    redacted = Redactor.redact_text(text, dynamic_secrets=secrets)
    assert "secret_token_val_123" not in redacted
    assert "[REDACTED_MY_TOKEN]" in redacted

def test_trust_boundary_default_restricted(tmp_path: Path):
    evaluator = TrustBoundaryEvaluator(project_root=tmp_path)
    res = evaluator.evaluate()
    assert res.is_trusted is False
    assert res.mode == "restricted"
    assert res.allow_python_contracts is False

def test_trust_boundary_trusted_marker(tmp_path: Path):
    harness_dir = tmp_path / ".harness"
    harness_dir.mkdir()
    (harness_dir / "trusted_repository").touch()

    evaluator = TrustBoundaryEvaluator(project_root=tmp_path)
    res = evaluator.evaluate()
    assert res.is_trusted is True
    assert res.mode == "trusted"
    assert res.allow_python_contracts is True

def test_universal_approval_rule_for_destructive_rollback():
    evaluator = TrustBoundaryEvaluator()
    # Hook destrutivo em repositório confiável AINDA exige aprovação (retorna False para auto-execução)
    can_auto_exec = evaluator.validate_rollback_hook(is_destructive=True, is_trusted_repo=True)
    assert can_auto_exec is False

    # Hook não destrutivo em repositório confiável pode auto-executar
    can_auto_exec_safe = evaluator.validate_rollback_hook(is_destructive=False, is_trusted_repo=True)
    assert can_auto_exec_safe is True
