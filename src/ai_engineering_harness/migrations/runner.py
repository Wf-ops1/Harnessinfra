"""Orquestrador de migrações automáticas de esquemas de projetos e estados legados."""

import json
from pathlib import Path
from typing import Dict, Any

class MigrationRunner:
    """Detecta versões antigas de esquemas do .harness/ e aplica migrações atômicas."""

    TARGET_VERSION = "1.0"

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_and_migrate_manifest((self) -> bool:
        project_yaml = self.project_root / ".harness" / "project.yaml"
        if not project_yaml.is_file():
            return False

        # Projeto já está no formato atual
        return True
