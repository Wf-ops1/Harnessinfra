"""Mapeamento de capacidades do ambiente local e ferramentas."""

from pydantic import BaseModel, ConfigDict


class SystemCapabilities(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    git_installed: bool
    python_version: str
    mcp_serena_available: bool
    mcp_codebase_memory_available: bool
    llm_providers_configured: bool
