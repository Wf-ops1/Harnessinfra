"""Adaptadores de provedores concretos."""

from .openai import OpenAIAdapter
from .anthropic import AnthropicAdapter
from .local import LocalAdapter

__all__ = ["OpenAIAdapter", "AnthropicAdapter", "LocalAdapter"]
