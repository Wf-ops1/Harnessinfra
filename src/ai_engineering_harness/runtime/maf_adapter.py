"""Typed loader for canonical compiled graph artifacts."""

from pathlib import Path

from ai_engineering_harness.contracts import CompiledGraphArtifact


class MAFAdapter:
    """Load and validate a canonical ``CompiledGraphArtifact`` before runtime."""

    @classmethod
    def load_and_validate(cls, compiled_json_path: Path) -> CompiledGraphArtifact:
        if not compiled_json_path.is_file():
            raise FileNotFoundError(f"compiled graph artifact not found: {compiled_json_path}")
        return CompiledGraphArtifact.model_validate_json(
            compiled_json_path.read_text(encoding="utf-8")
        )
