"""Tamper-Evident Linear Hash Chain Audit Trail."""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

class AuditTrailManager:
    """Gerencia o log append-only event-journal.jsonl com SHA-256 encadeado."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, project_root: Path, execution_id: str):
        self.exec_dir = project_root / ".harness" / "state" / "executions" / execution_id
        self.exec_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.exec_dir / "event-journal.jsonl"
        self.last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        if not self.journal_file.is_file():
            return self.GENESIS_HASH
        lines = self.journal_file.read_text(encoding="utf-8").strip().split("\n")
        if not lines or not lines[-1]:
            return self.GENESIS_HASH
        last_entry = json.loads(lines[-1])
        return last_entry.get("current_hash", self.GENESIS_HASH)

    def log_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()

        event_data = {
            "event_type": event_type,
            "timestamp": timestamp,
            "payload": payload,
            "previous_hash": self.last_hash
        }

        # Calcular o hash SHA-256 encadeado: Hash_N = SHA256(Evento_N || Hash_N-1)
        raw_bytes = (json.dumps(event_data, sort_keys=True) + self.last_hash).encode("utf-8")
        current_hash = hashlib.sha256(raw_bytes).hexdigest()

        event_data["current_hash"] = current_hash
        self.last_hash = current_hash

        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_data) + "\n")

        return event_data

    def verify_integrity(self) -> Tuple[bool, str]:
        """Verifica a integridade da Hash Chain percorrendo todas as linhas."""
        if not self.journal_file.is_file():
            return True, "Journal vazio."

        lines = self.journal_file.read_text(encoding="utf-8").strip().split("\n")
        expected_prev_hash = self.GENESIS_HASH

        for idx, line in enumerate(lines):
            if not line:
                continue
            entry = json.loads(line)

            if entry.get("previous_hash") != expected_prev_hash:
                return False, f"Quebra de corrente na linha {idx+1}: previous_hash inválido."

            stored_hash = entry.pop("current_hash")
            raw_bytes = (json.dumps(entry, sort_keys=True) + expected_prev_hash).encode("utf-8")
            calculated_hash = hashlib.sha256(raw_bytes).hexdigest()

            if stored_hash != calculated_hash:
                return False, f"Adulteração detectada na linha {idx+1}: hash alterado."

            expected_prev_hash = stored_hash

        return True, "Integridade da Hash Chain 100% verificada."

    def export_json(self) -> str:
        """Retorna todo o histórico de eventos formatado como JSON estruturado."""
        if not self.journal_file.is_file():
            return json.dumps({"execution_id": getattr(self, "execution_id", "unknown"), "events": []}, indent=2)

        lines = [line for line in self.journal_file.read_text(encoding="utf-8").strip().split("\n") if line]
        events = [json.loads(line) for line in lines]
        return json.dumps({
            "execution_id": getattr(self, "execution_id", "unknown"),
            "total_events": len(events),
            "events": events
        }, indent=2)

    def export_sarif(self) -> str:
        """Converte os eventos do audit log para o formato de relatório SARIF v2.1.0."""
        is_valid, msg = self.verify_integrity()
        lines = []
        if self.journal_file.is_file():
            lines = [line for line in self.journal_file.read_text(encoding="utf-8").strip().split("\n") if line]

        runs_results = []
        for idx, line in enumerate(lines):
            entry = json.loads(line)
            runs_results.append({
                "ruleId": f"AUDIT-EVENT-{(entry.get('event_type') or 'GENERIC').upper()}",
                "level": "note" if is_valid else "error",
                "message": {
                    "text": f"Evento {entry.get('event_type')} registrado no timestamp {entry.get('timestamp')}"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f".harness/state/executions/{getattr(self, 'execution_id', '')}/event-journal.jsonl"
                            },
                            "region": {
                                "startLine": idx + 1
                            }
                        }
                    }
                ]
            })

        sarif_doc = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "AI-Engineering-Harness Audit Trail",
                            "version": "0.1.0"
                        }
                    },
                    "results": runs_results
                }
            ]
        }
        return json.dumps(sarif_doc, indent=2)

