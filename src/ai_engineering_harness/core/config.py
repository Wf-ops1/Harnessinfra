"""Resolução hierárquica de configuração em 6 níveis.

Ordem de Precedência (Menor para Maior):
1. Defaults do Pacote (ai_engineering_harness.defaults)
2. Perfil Selecionado (profiles/<name>.yaml)
3. Manifesto do Projeto (.harness/project.yaml)
4. Overrides do Time (.harness/bmad/custom/*.toml)
5. Overrides Pessoais (.harness/bmad/custom/*.user.toml)
6. Argumentos da CLI (Maior Prioridade)
"""

from pathlib import Path
from typing import Any

import yaml

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore

def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Realiza o merge recursivo de dicionários."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

class ConfigResolver:
    """Carrega e mescla a configuração efetiva do motor em 6 níveis."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

    def resolve(
        self,
        profile_name: str = "default",
        cli_overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        config: dict[str, Any] = {}

        # 1. Defaults do Pacote
        package_defaults = {
            "version": "1.0",
            "context_sufficiency_threshold": 0.72,
            "approval_policy": "strict",
            "data_egress": {"allowed_providers": ["openai", "anthropic", "local"]},
            "models": {
                "providers": {
                    "openai": {
                        "adapter": "openai",
                        "model": "gpt-4o",
                        "api_key_env": "OPENAI_API_KEY",
                    },
                    "anthropic": {
                        "adapter": "anthropic",
                        "model": "claude-3-5-sonnet",
                        "api_key_env": "ANTHROPIC_API_KEY",
                    },
                    "local": {
                        "adapter": "local",
                        "model": "llama3",
                        "base_url": "http://127.0.0.1:11434/v1",
                    },
                },
                "routing": {
                    "primary_provider": "local",
                    "fallback_providers": [],
                },
            },
            "budget": {"max_tokens": 100000},
            "verification": {"enforce_applicable_only": True},
        }
        config = deep_merge(config, package_defaults)

        # 2. Perfil Selecionado
        profile_path = self.project_root / ".harness" / "profiles" / f"{profile_name}.yaml"
        if profile_path.is_file():
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_data = yaml.safe_load(f) or {}
                config = deep_merge(config, profile_data)

        # 3. Manifesto do Projeto (.harness/project.yaml)
        project_manifest = self.project_root / ".harness" / "project.yaml"
        if project_manifest.is_file():
            with open(project_manifest, "r", encoding="utf-8") as f:
                manifest_data = yaml.safe_load(f) or {}
                config = deep_merge(config, {"project": manifest_data})

        # 4. Overrides do Time (.harness/bmad/custom/*.toml)
        custom_dir = self.project_root / ".harness" / "bmad" / "custom"
        if custom_dir.is_dir():
            for toml_file in sorted(custom_dir.glob("*.toml")):
                if not toml_file.name.endswith(".user.toml"):
                    with open(toml_file, "rb") as f:
                        config = deep_merge(config, tomllib.load(f))

        # 5. Overrides Pessoais (.harness/bmad/custom/*.user.toml)
        if custom_dir.is_dir():
            for user_toml in sorted(custom_dir.glob("*.user.toml")):
                with open(user_toml, "rb") as f:
                    config = deep_merge(config, tomllib.load(f))

        # 6. Argumentos da CLI (Maior Prioridade)
        if cli_overrides:
            config = deep_merge(config, cli_overrides)

        from ai_engineering_harness.models.router import ModelRouter

        ModelRouter.validate_effective_config(config)
        return config
