"""Módulo Tools: Roteamento de ferramentas, permissões e adaptadores."""

from .permissions import ToolPermissions
from .router import (
    ToolDefinition,
    ToolExecutionError,
    ToolPayloadValidationError,
    ToolRegistration,
    ToolRouter,
    ToolRouterError,
    ToolUnauthorizedError,
    ToolUnavailableError,
)

__all__ = [
    "ToolDefinition",
    "ToolExecutionError",
    "ToolPayloadValidationError",
    "ToolPermissions",
    "ToolRegistration",
    "ToolRouter",
    "ToolRouterError",
    "ToolUnauthorizedError",
    "ToolUnavailableError",
]
