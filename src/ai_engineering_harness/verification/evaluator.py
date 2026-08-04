"""Avaliador de comandos de verificação mapeados por linguagem."""

from typing import Dict, Optional

class VerificationEvaluator:
    """Mapeia os tipos abstratos de gate para os comandos nativos da stack."""

    _commands_by_language: Dict[str, Dict[str, str]] = {
        "python": {
            "typecheck": "mypy .",
            "lint": "ruff check .",
            "unit_test": "pytest",
            "build": "python -m build"
        },
        "typescript/javascript": {
            "typecheck": "tsc",
            "lint": "eslint .",
            "unit_test": "vitest run",
            "build": "npm run build"
        },
        "go": {
            "typecheck": "go vet ./...",
            "lint": "golangci-lint run",
            "unit_test": "go test ./...",
            "build": "go build ./..."
        },
        "rust": {
            "typecheck": "cargo check",
            "lint": "cargo clippy",
            "unit_test": "cargo test",
            "build": "cargo build"
        },
        "java": {
            "typecheck": "mvn compile",
            "lint": "mvn checkstyle:check",
            "unit_test": "mvn test",
            "build": "mvn package"
        }
    }

    _aliases: Dict[str, str] = {
        "py": "python",
        "js": "typescript/javascript",
        "ts": "typescript/javascript",
        "javascript": "typescript/javascript",
        "typescript": "typescript/javascript",
        "node": "typescript/javascript",
        "golang": "go"
    }

    @classmethod
    def get_command(cls, language: str, gate_type: str) -> Optional[str]:
        lang_key = language.lower().strip()
        lang_key = cls._aliases.get(lang_key, lang_key)
        lang_gates = cls._commands_by_language.get(lang_key, {})
        return lang_gates.get(gate_type)

