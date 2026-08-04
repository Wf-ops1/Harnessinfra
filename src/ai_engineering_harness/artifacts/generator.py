"""Gerador de relatórios de evidências em .harness/artifacts/latest.json."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ArtifactGenerator:
    """Consolida os resultados da execução e gera evidências finais."""

    def __init__(self, project_root: Path):
        self.artifacts_dir = project_root / ".harness" / "artifacts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def generate_latest_report(self, execution_id: str, summary: dict[str, Any]) -> Path:
        data = {
            "execution_id": execution_id,
            "generated_at_iso": datetime.now(UTC).isoformat(),
            "summary": summary
        }

        report_path = self.artifacts_dir / "latest.json"
        report_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return report_path
