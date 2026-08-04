"""Mapeamento de capacidades dos modelos configurados."""

from pydantic import BaseModel, ConfigDict

class ModelCapabilities(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    supports_streaming: bool = True
    supports_tool_calling: bool = True
    supports_structured_output: bool = True
    max_context_window: int = 128000
