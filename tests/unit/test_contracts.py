"""Testes unitários de validação e serialização dos contratos Pydantic nativos (TASK-1.2)."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from ai_engineering_harness.contracts.events import ExecutionEvent, KnowledgeSyncEvent
from ai_engineering_harness.contracts.nodes import ArchitectureAnalysis, CodeGenNode, ContextSufficiencyReport
from ai_engineering_harness.contracts.transactions import KnowledgeTransaction, JournalState

def test_execution_event_serialization():
    now = datetime.now(timezone.utc)
    event = ExecutionEvent(
        event_id="evt-100",
        execution_id="exec-42",
        event_type="STEP_COMPLETED",
        timestamp=now,
        payload={"step": "code_gen", "status": "GREEN"},
        previous_hash="hash-1",
        current_hash="hash-2"
    )
    json_str = event.model_dump_json()
    restored = ExecutionEvent.model_validate_json(json_str)
    assert restored.event_id == "evt-100"
    assert restored.execution_id == "exec-42"
    assert restored.payload["status"] == "GREEN"

def test_context_sufficiency_report():
    report = ContextSufficiencyReport(
        score=0.85,
        threshold_required=0.72,
        is_sufficient=True,
        dimensions={"kis": 0.9, "ast": 0.8}
    )
    assert report.is_sufficient is True
    assert report.score >= report.threshold_required

def test_knowledge_transaction_strict_validation():
    now = datetime.now(timezone.utc)
    tx = KnowledgeTransaction(
        tx_id="tx-99",
        status="COMMITTED",
        created_at=now,
        staging_path=".harness/knowledge/staging/tx-99/",
        artifact_ids=["ki-1", "ki-2"]
    )
    assert tx.status == "COMMITTED"
    
    with pytest.raises(ValidationError):
        # Campos faltantes devem disparar ValidationError
        KnowledgeTransaction(tx_id="tx-100")
