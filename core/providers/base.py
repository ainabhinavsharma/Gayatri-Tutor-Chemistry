"""Gayatri AI — LLM Provider base interface.

Defines the contract that all LLM providers (local + cloud) must implement.
No provider-specific logic here — just the interface and shared types.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("gayatri.providers")


class SpeedTier(str, Enum):
    """Relative speed classification for model routing."""
    FAST = "fast"         # Groq, Flash, mini models
    MEDIUM = "medium"     # Standard cloud models
    SLOW = "slow"         # Large reasoning models, local


class ProviderStatus(str, Enum):
    """Operational status classification for providers (Audit #PROVIDER-002)."""
    READY = "ready"
    AUTH_REQUIRED = "auth_required"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED = "unsupported"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


class Capability(str, Enum):
    """Model capability flags."""
    CHAT = "chat"
    STREAM = "stream"
    TOOLS = "tools"
    VISION = "vision"
    JSON_MODE = "json_mode"
    SYSTEM_PROMPT = "system_prompt"
    LONG_CONTEXT = "long_context"


class CatalogSource(str, Enum):
    """Source of model metadata catalog."""
    LIVE = "live"          # Fetched directly from the provider API
    FALLBACK = "fallback"  # Static fallback / offline knowledge base


@dataclass
class ModelInfo:
    """Normalized model metadata for the unified catalog."""
    id: str                  # provider-specific model id (e.g. "gpt-4o", "claude-sonnet-4-20250514")
    name: str                # human-readable name
    provider: str            # provider key (e.g. "openai", "anthropic", "google", "local")
    context_length: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    speed_tier: SpeedTier = SpeedTier.MEDIUM
    capabilities: list[Capability] = field(default_factory=list)
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json: bool = False
    catalog_source: CatalogSource = CatalogSource.FALLBACK

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "context_length": self.context_length,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "speed_tier": self.speed_tier.value,
            "capabilities": [c.value for c in self.capabilities],
            "supports_tools": self.supports_tools,
            "supports_vision": self.supports_vision,
            "supports_json": self.supports_json,
            "catalog_source": self.catalog_source.value if isinstance(self.catalog_source, CatalogSource) else str(self.catalog_source),
        }


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""
    role: str          # "system", "user", "assistant", "tool"
    content: str = ""
    tool_calls: list[dict] | None = None
    tool_call_id: str = ""

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ChatOptions:
    """Options for a chat completion request."""
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 0.9
    top_k: int = 40
    stop: list[str] = field(default_factory=list)
    tools: list[dict] | None = None
    json_mode: bool = False
    stream: bool = False


@dataclass
class ChatResponse:
    """A completed chat response."""
    text: str
    model_id: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    tool_calls: list[dict] | None = None


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Each provider (local, OpenAI, Anthropic, Google) implements this interface.
    The orchestrator and router call through this interface — no provider-specific
    logic leaks into the rest of the app.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g. 'OpenAI', 'Anthropic', 'Local')."""
        ...

    @property
    @abstractmethod
    def key(self) -> str:
        """Machine key (e.g. 'openai', 'anthropic', 'google', 'local')."""
        ...

    @abstractmethod
    def validate_key(self) -> tuple[bool, str]:
        """Validate the API key / model availability.

        Returns:
            (is_valid, message) — message is error detail or "OK"
        """
        ...

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """Return available models for this provider."""
        ...

    @abstractmethod
    def chat(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> ChatResponse:
        """Send a chat completion request (non-streaming)."""
        ...

    @abstractmethod
    def stream(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> Iterator[str]:
        """Stream tokens from a chat completion request.

        Yields string chunks.
        """
        ...

    def supports_tools(self) -> bool:
        """Whether this provider supports function/tool calling."""
        return False

    def supports_vision(self) -> bool:
        """Whether this provider supports image inputs."""
        return False

    def supports_json(self) -> bool:
        """Whether this provider supports JSON mode output."""
        return False

    @property
    def is_local(self) -> bool:
        """Whether this provider executes purely locally on-device."""
        return self.key == "local"

    @property
    def catalog_source(self) -> CatalogSource:
        """Whether this provider's catalog was obtained from live API or fallback."""
        return getattr(self, "_catalog_source", CatalogSource.FALLBACK)

    @property
    def is_authenticated(self) -> bool:
        """Whether valid credentials/keys are configured for this provider."""
        if self.is_local:
            return True
        key = getattr(self, "_api_key", None)
        return bool(key and str(key).strip())

    @property
    def is_reachable(self) -> bool:
        """Whether the provider API endpoint is reachable."""
        return getattr(self, "_is_reachable", True if self.is_authenticated else False)

    def is_ready(self) -> bool:
        """Whether the provider is authenticated, reachable, and has available models."""
        return self.is_authenticated and self.is_reachable

    def get_status(self) -> ProviderStatus:
        """Return the detailed provider operational status (Audit #PROVIDER-002)."""
        if not self.is_authenticated:
            return ProviderStatus.AUTH_REQUIRED
        if not self.is_reachable or not self.is_ready():
            return ProviderStatus.OFFLINE
        return ProviderStatus.READY

    def get_cached_models(self, ttl_seconds: float = 600.0) -> list[ModelInfo]:
        """Return cached models if within TTL, else fetch fresh (Audit #PROVIDER-004)."""
        import time
        cached_models = getattr(self, "_cached_models", None)
        cached_at = getattr(self, "_cached_models_timestamp", 0.0)
        now = time.time()

        if cached_models is not None and (now - cached_at) < ttl_seconds:
            return cached_models

        fresh_models = self.list_models()
        self._cached_models = fresh_models
        self._cached_models_timestamp = now
        return fresh_models

    def check_privacy_policy(self) -> None:
        """Enforce privacy policy and log transmission audit for cloud providers."""
        if not self.is_local:
            try:
                from core.config import ExecutionMode
                from core.settings import get_settings
                mode = get_settings().get("privacy_mode", "local_only")
                if mode == "local_only" or mode == ExecutionMode.LOCAL_ONLY.value:
                    raise PermissionError(
                        f"Data cannot leave the device: provider '{self.name}' ({self.key}) "
                        "is blocked because privacy mode is set to 'local_only'."
                    )
                # P0-005: Per-request transmission audit when cloud-allowed
                import logging
                audit_logger = logging.getLogger("gayatri.privacy.audit")
                audit_logger.info(f"TRANSMISSION_AUDIT: User-approved cloud request sent to provider '{self.name}' ({self.key}) in cloud_allowed mode.")
            except ImportError:
                pass

    def __repr__(self) -> str:
        return f"<LLMProvider {self.name} ({self.key})>"
