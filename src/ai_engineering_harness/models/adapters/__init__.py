"""Adaptadores de provedores concretos."""

from .anthropic import AnthropicAdapter
from .local import LocalAdapter
from .openai import OpenAIAdapter

__all__ = ["AnthropicAdapter", "LocalAdapter", "OpenAIAdapter"]
