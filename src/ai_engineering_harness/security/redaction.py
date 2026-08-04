"""Sanitizador e redator automático de segredos em textos e logs."""

import re
from typing import ClassVar


class Redactor:
    """Substitui segredos e tokens sensíveis por placeholders de redação."""

    # Padrões regex para chaves conhecidas
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"sk-[a-zA-Z0-9]{32,}", re.IGNORECASE),          # OpenAI API Keys
        re.compile(r"sk-ant-[a-zA-Z0-9_-]{32,}", re.IGNORECASE),    # Anthropic API Keys
        re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+"), # JWTs
        re.compile(r"-----BEGIN (RSA|OPENSSH) PRIVATE KEY-----[\s\S]+?-----END \1 PRIVATE KEY-----"), # Private Keys
        re.compile(r'(?i)(?:password|secret|api_key|token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'), # Pares Chave=Valor
    ]

    @classmethod
    def redact_text(cls, text: str, dynamic_secrets: dict[str, str] | None = None) -> str:
        """Sanitiza o texto removendo padrões conhecidos e valores dinâmicos de memória."""
        if not text:
            return text

        redacted = text

        # 1. Substituir valores dinâmicos passados ou carregados do ambiente
        if dynamic_secrets:
            for key, val in dynamic_secrets.items():
                if val and len(val) > 4:
                    redacted = redacted.replace(val, f"[REDACTED_{key}]")

        # 2. Aplicar regras regex gerais
        for pattern in cls._patterns:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)

        return redacted
