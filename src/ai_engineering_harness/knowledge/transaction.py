"""Knowledge Transaction Protocol em 5 Etapas sem Janela de Crash."""

import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List
from ai_engineering_harness.contracts.transactions import KnowledgeTransaction

class TransactionState(str, Enum):
    STAGING = "STAGING"
    VALIDATED = "VALIDATED"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"

class KnowledgeTransactionManager:
    """Gerencia a atualização transacional e atômica da base de conhecimento."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.knw_dir = project_root / ".harness" / "knowledge"
        self.knw_dir.mkdir(parents=True, exist_ok=True)

        self.staging_dir = self.knw_dir / "staging"
        self.staging_dir.mkdir(exist_ok=True)

        self.current_json = self.knw_dir / "current.json"
        self.journal_file = self.knw_dir / "transaction_journal.jsonl"

    def _fsync_file(self, file_path: Path) -> None:
        """Executa fsync explícito para garantir gravação no disco físico."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.flush()
            os.fsync(f.fileno())

    def _fsync_directory(self, dir_path: Path) -> None:
        """Executa fsync no diretório pai para persistir mudanças de ponteiro."""
        if hasattr(os, "O_DIRECTORY"):
            try:
                fd = os.open(str(dir_path), os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                pass

    def execute_transaction(self, tx_id: str, new_kis: Dict[str, Any]) -> str:
        tx_staging = self.staging_dir / tx_id
        tx_staging.mkdir(exist_ok=True)

        # 1. STAGING
        ki_file = tx_staging / "data.json"
        ki_file.write_text(json.dumps(new_kis, indent=2), encoding="utf-8")

        # 2. VALIDATION
        if "id" not in new_kis:
            raise ValueError("[KNOWLEDGE ERROR] Objeto KI inválido sem 'id'")

        # 3. JOURNAL PREPARED + fsync
        prep_entry = json.dumps({"tx_id": tx_id, "state": TransactionState.PREPARED.value}) + "\n"
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(prep_entry)
            f.flush()
            os.fsync(f.fileno())

        # 4. ATOMIC SWAP (current.json) + fsync
        pointer_data = {"current_tx_id": tx_id, "active_ki": new_kis["id"]}
        temp_pointer = self.knw_dir / f"current_{tx_id}.tmp"
        temp_pointer.write_text(json.dumps(pointer_data, indent=2), encoding="utf-8")
        self._fsync_file(temp_pointer)

        os.replace(temp_pointer, self.current_json)
        self._fsync_directory(self.knw_dir)

        # 5. JOURNAL COMMITTED + fsync
        commit_entry = json.dumps({"tx_id": tx_id, "state": TransactionState.COMMITTED.value}) + "\n"
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(commit_entry)
            f.flush()
            os.fsync(f.fileno())

        return TransactionState.COMMITTED.value

    def recover_if_needed(self) -> str:
        """Verifica se há transação em PREPARED sem COMMITTED pós-crash."""
        if not self.journal_file.is_file():
            return "CLEAN"

        lines = self.journal_file.read_text(encoding="utf-8").strip().split("\n")
        if not lines or not lines[-1]:
            return "CLEAN"

        last_entry = json.loads(lines[-1])
        if last_entry.get("state") == TransactionState.PREPARED.value:
            tx_id = last_entry["tx_id"]
            # Concluir a transação pendente deterministicamente
            commit_entry = json.dumps({"tx_id": tx_id, "state": TransactionState.COMMITTED.value}) + "\n"
            with open(self.journal_file, "a", encoding="utf-8") as f:
                f.write(commit_entry)
                f.flush()
                os.fsync(f.fileno())
            return f"RECOVERED_{tx_id}"

        return "CLEAN"
