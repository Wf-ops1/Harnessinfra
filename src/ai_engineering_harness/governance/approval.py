"""Gerenciador de pontos de interrupção e aprovação humana."""

import json
from pathlib import Path


class ApprovalManager:
    """Gerencia a solicitação e confirmação de aprovação humana."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def create_approval_request(self, execution_id: str, reason: str) -> Path:
        req_dir = self.project_root / ".harness" / "state" / "executions" / execution_id
        req_dir.mkdir(parents=True, exist_ok=True)
        req_file = req_dir / "approval_request.json"

        data = {
            "execution_id": execution_id,
            "status": "PENDING",
            "reason": reason
        }
        req_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return req_file

    def approve(self, execution_id: str) -> bool:
        req_file = self.project_root / ".harness" / "state" / "executions" / execution_id / "approval_request.json"
        if not req_file.is_file():
            return False

        data = json.loads(req_file.read_text(encoding="utf-8"))
        data["status"] = "APPROVED"
        req_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True

    def get_approval_status(self, execution_id: str) -> str | None:
        req_file = self.project_root / ".harness" / "state" / "executions" / execution_id / "approval_request.json"
        if not req_file.is_file():
            return None
        data = json.loads(req_file.read_text(encoding="utf-8"))
        return data.get("status")

