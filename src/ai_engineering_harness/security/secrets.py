"""Gerenciador seguro de secrets exclusivamente em memória."""

import os
from typing import ClassVar


class SecretManager:
    """Carrega chaves e tokens de variáveis de ambiente sem persistir no disco."""

    _sensitive_keys: ClassVar[list[str]] = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SERENA_MCP_TOKEN",
        "CODEBASE_MEMORY_TOKEN",
        "HARNESS_SECRET_KEY"
    ]

    @classmethod
    def get_secret(cls, key: str, default: str | None = None) -> str | None:
        """Recupera o segredo do ambiente de forma segura."""
        return os.environ.get(key, default)

    @classmethod
    def load_all_known_secrets(cls) -> dict[str, str]:
        """Retorna os segredos conhecidos atualmente em memória para sanitização."""
        found = {}
        for key in cls._sensitive_keys:
            val = os.environ.get(key)
            if val:
                found[key] = val
        return found
