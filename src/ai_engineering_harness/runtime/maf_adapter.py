"""Executor e validador de artefato MAF JSON versionado."""

import json
from pathlib import Path
from typing import Any


class MAFAdapter:
    """Valida o cabeçalho de versão do MAF JSON antes de iniciar o runtime."""

    @classmethod
    def load_and_validate(cls, compiled_json_path: Path) -> dict[str, Any]:
        if not compiled_json_path.is_file():
            raise FileNotFoundError(f"Artefato MAF não encontrado: {compiled_json_path}")

        artifact = json.loads(compiled_json_path.read_text(encoding="utf-8"))
        header = artifact.get("header", {})

        if header.get("runtime_provider") != "maf":
            raise ValueError(f"Provedor de runtime incompatível: {header.get('runtime_provider')}")

        return artifact
