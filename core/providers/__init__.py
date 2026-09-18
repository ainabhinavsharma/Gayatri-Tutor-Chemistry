"""LLM providers — local (llama-cpp-python) and cloud adapters."""

from core.providers.anthropic import AnthropicProvider
from core.providers.base import (
    Capability,
    CatalogSource,
    ChatMessage,
    ChatOptions,
    ChatResponse,
    LLMProvider,
    ModelInfo,
    SpeedTier,
)
from core.providers.google import GoogleProvider
from core.providers.local import LocalLLMProvider, LocalModelError, LocalProvider, format_gemma_prompt
from core.providers.openai_compat import OpenAICompatibleProvider

__all__ = [
    # Base
    "LLMProvider", "ModelInfo", "ChatMessage", "ChatOptions", "ChatResponse",
    "SpeedTier", "Capability", "CatalogSource",
    # Providers
    "LocalProvider", "LocalLLMProvider", "LocalModelError", "format_gemma_prompt",
    "OpenAICompatibleProvider", "AnthropicProvider", "GoogleProvider",
]
