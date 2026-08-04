"""FSM de Estado do Workflow e Persistência Local em Tempo Real."""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone

ROLLBACK_REQUESTED = "ROLLBACK_REQUESTED"
ROLLBACK_CODE_COMPLETED = "ROLLBACK_CODE_COMPLETED"
ROLLBACK_EFFECTS_COMPLETED = "ROLLBACK_EFFECTS_COMPLETED"
EXECUTION_COMPENSATED = "EXECUTION_COMPENSATED"


class InvalidStateTransitionError(ValueError):
    """Exceção lançada quando ocorre uma transição inválida no FSM."""
    pass


class WorkflowState(str, Enum):
    INITIATED = "INITIATED"
    CONTEXT_ASSEMBLING = "CONTEXT_ASSEMBLING"
    BLOCKED_INSUFFICIENT_CONTEXT = "BLOCKED_INSUFFICIENT_CONTEXT"
    PLANNING = "PLANNING"
    GENERATING_PLAN = "GENERATING_PLAN"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    PROMOTING = "PROMOTING"
    REINDEXING = "REINDEXING"
    KNOWLEDGE_SYNC = "KNOWLEDGE_SYNC"
    GENERATING_EVIDENCE = "GENERATING_EVIDENCE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FAILED_RETRY_EXHAUSTED = "FAILED_RETRY_EXHAUSTED"


VALID_TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
    WorkflowState.INITIATED: {
        WorkflowState.CONTEXT_ASSEMBLING,
        WorkflowState.PLANNING,
        WorkflowState.GENERATING_PLAN,
        WorkflowState.EXECUTING,
        WorkflowState.FAILED,
    },
    WorkflowState.CONTEXT_ASSEMBLING: {
        WorkflowState.GENERATING_PLAN,
        WorkflowState.PLANNING,
        WorkflowState.BLOCKED_INSUFFICIENT_CONTEXT,
        WorkflowState.FAILED,
    },
    WorkflowState.BLOCKED_INSUFFICIENT_CONTEXT: {
        WorkflowState.CONTEXT_ASSEMBLING,
        WorkflowState.FAILED,
    },
    WorkflowState.PLANNING: {
        WorkflowState.GENERATING_PLAN,
        WorkflowState.EXECUTING,
        WorkflowState.FAILED,
    },
    WorkflowState.GENERATING_PLAN: {
        WorkflowState.EXECUTING,
        WorkflowState.FAILED,
    },
    WorkflowState.EXECUTING: {
        WorkflowState.VERIFYING,
        WorkflowState.FAILED,
        WorkflowState.FAILED_RETRY_EXHAUSTED,
    },
    WorkflowState.VERIFYING: {
        WorkflowState.AWAITING_APPROVAL,
        WorkflowState.PROMOTING,
        WorkflowState.EXECUTING,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.FAILED_RETRY_EXHAUSTED,
    },
    WorkflowState.AWAITING_APPROVAL: {
        WorkflowState.PROMOTING,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.PROMOTING: {
        WorkflowState.REINDEXING,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.REINDEXING: {
        WorkflowState.KNOWLEDGE_SYNC,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.KNOWLEDGE_SYNC: {
        WorkflowState.GENERATING_EVIDENCE,
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.GENERATING_EVIDENCE: {
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
    },
    WorkflowState.COMPLETED: set(),
    WorkflowState.FAILED: set(),
    WorkflowState.FAILED_RETRY_EXHAUSTED: set(),
}


class WorkflowStateMachine:
    """Finite State Machine persistida em .harness/state/executions/<exec_id>/workflow-state.json."""

    def __init__(self, project_root: Path, execution_id: str):
        self.project_root = project_root
        self.execution_id = execution_id
        self.exec_dir = project_root / ".harness" / "state" / "executions" / execution_id
        self.exec_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.exec_dir / "workflow-state.json"

        self.current_state = WorkflowState.INITIATED
        self._save_state()

    def _save_state(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        data = {
            "execution_id": self.execution_id,
            "state": self.current_state.value if isinstance(self.current_state, WorkflowState) else str(self.current_state),
            "updated_at_iso": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def transition_to(self, new_state: WorkflowState, metadata: Optional[Dict[str, Any]] = None) -> None:
        target_state = new_state
        if isinstance(new_state, str) and not isinstance(new_state, WorkflowState):
            try:
                target_state = WorkflowState(new_state)
            except ValueError:
                pass

        allowed_transitions = VALID_TRANSITIONS.get(self.current_state, set())
        if target_state not in allowed_transitions:
            curr_str = self.current_state.value if isinstance(self.current_state, WorkflowState) else str(self.current_state)
            tgt_str = target_state.value if isinstance(target_state, WorkflowState) else str(target_state)
            raise InvalidStateTransitionError(f"Transição de estado inválida: {curr_str} -> {tgt_str}")

        self.current_state = target_state
        self._save_state(metadata)
