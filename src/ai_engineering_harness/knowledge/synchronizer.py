"""Sincronizador de KIs do projeto."""

from pathlib import Path
from typing import Dict, Any
from ai_engineering_harness.knowledge.transaction import KnowledgeTransactionManager

class KnowledgeSynchronizer:
    """Orquestra a sincronização atômica de KIs."""

    def __init__(self, project_root: Path):
        self.tx_mgr = KnowledgeTransactionManager(project_root)

    def sync_ki(self, tx_id: str, ki_data: Dict[str, Any]) -> str:
        # Tentar recuperar pendências antes
        self.tx_mgr.recover_if_needed()
        return self.tx_mgr.execute_transaction(tx_id, ki_data)
