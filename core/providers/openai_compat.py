"""Gayatri AI — OpenAI-compatible provider.

Covers: OpenAI, , Groq, DeepSeek, Mistral, Together, Together AI,
and any other provider with an OpenAI-compatible /v1/chat/completions endpoint.

Configured via base_url + api_key.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator

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

logger = logging.getLogger("gayatri.providers.openai_compat")

# Known model → tier mappings
_KNOWN_MODELS: dict[str, dict] = {
    # OpenAI
    "gpt-4o": {"name": "GPT-4o", "ctx": 128000, "speed": SpeedTier.MEDIUM, "tools": True, "vision": True, "json": True},
    "gpt-4o-mini": {"name": "GPT-4o Mini", "ctx": 128000, "speed": SpeedTier.FAST, "tools": True, "vision": True, "json": True},
    "gpt-4-turbo": {"name": "GPT-4 Turbo", "ctx": 128000, "speed": SpeedTier.MEDIUM, "tools": True, "vision": True, "json": True},
    "gpt-4": {"name": "GPT-4", "ctx": 8192, "speed": SpeedTier.MEDIUM, "tools": True, "json": True},
    "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "ctx": 16385, "speed": SpeedTier.FAST, "tools": True, "json": True},
    "o1": {"name": "o1", "ctx": 128000, "speed": SpeedTier.SLOW, "tools": False, "json": False},
    "o1-mini": {"name": "o1 Mini", "ctx": 128000, "speed": SpeedTier.SLOW, "tools": False, "json": False},
    "o3": {"name": "o3", "ctx": 200000, "speed": SpeedTier.SLOW, "tools": True, "json": False},
    "o3-mini": {"name": "o3 Mini", "ctx": 200000, "speed": SpeedTier.SLOW, "tools": True, "json": False},
    # Groq
    "llama-3.3-70b-versatile": {"name": "Llama 3.3 70B (Groq)", "ctx": 32768, "speed": SpeedTier.FAST, "tools": True, "json": True},
    "llama-3.1-8b-instant": {"name": "Llama 3.1 8B (Groq)", "ctx": 32768, "speed": SpeedTier.FAST, "tools": True, "json": True},
    "gemma2-9b-it": {"name": "Gemma 2 9B (Groq)", "ctx": 8192, "speed": SpeedTier.FAST, "tools": True, "json": True},
    "mixtral-8x7b-32768": {"name": "Mixtral 8x7B (Groq)", "ctx": 32768, "speed": SpeedTier.FAST, "tools": True, "json": True},
    # DeepSeek
    "deepseek-chat": {"name": "DeepSeek Chat", "ctx": 64000, "speed": SpeedTier.MEDIUM, "tools": True, "json": True},
    "deepseek-reasoner": {"name": "DeepSeek Reasoner", "ctx": 64000, "speed": SpeedTier.SLOW, "tools": False, "json": False},
    # Mistral
    "mistral-large-latest": {"name": "Mistral Large", "ctx": 32000, "speed": SpeedTier.MEDIUM, "tools": True, "json": True},
    "mistral-medium-latest": {"name": "Mistral Medium", "ctx": 32000, "speed": SpeedTier.MEDIUM, "tools": True, "json": True},
    "mistral-small-latest": {"name": "Mistral Small", "ctx": 32000, "speed": SpeedTier.FAST, "tools": True, "json": True},
    "open-mistral-nemo": {"name": "Mistral Nemo", "ctx": 128000, "speed": SpeedTier.FAST, "tools": True, "json": True},
    # Together
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": {"name": "Llama 3.3 70B (Together)", "ctx": 8192, "speed": SpeedTier.FAST, "tools": True, "json": True},
}


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible API provider.

    Works with any provider that implements the /v1/chat/completions API.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 name: str = "OpenAI", key: str = "openai"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._name = name
        self._key = key
        self._models: list[ModelInfo] | None = None
        self._catalog_source: CatalogSource = CatalogSource.FALLBACK
        self._is_reachable: bool = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def key(self) -> str:
        return self._key

    @property
    def catalog_source(self) -> CatalogSource:
        return self._catalog_source

    @property
    def is_authenticated(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    @property
    def is_reachable(self) -> bool:
        return self._is_reachable

    def is_ready(self) -> bool:
        return (
            self.is_authenticated
            and self._is_reachable
            and len(self._models or []) > 0
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def validate_key(self) -> tuple[bool, str]:
        """Validate key by fetching models list (cheap)."""
        if not self.is_authenticated:
            self._is_reachable = False
            return False, "API key not configured"

        try:
            import httpx
            response = httpx.get(
                f"{self._base_url}/models",
                headers=self._headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                self._is_reachable = True
                return True, "OK"
            elif response.status_code == 401:
                self._is_reachable = True
                return False, "Invalid API key"
            else:
                self._is_reachable = True
                return False, f"HTTP {response.status_code}: {response.text[:200]}"
        except ImportError:
            return False, "httpx not installed"
        except Exception as exc:
            self._is_reachable = False
            from core.errors import sanitize_message
            return False, sanitize_message(str(exc))[:200]

    def _get_client(self):
        """Lazy import httpx."""
        try:
            import httpx
            return httpx
        except ImportError:
            raise RuntimeError("httpx not installed. Run: pip install httpx")

    def list_models(self) -> list[ModelInfo]:
        """Fetch models from API, normalize with known model metadata."""
        if self._models is not None:
            return self._models

        httpx = self._get_client()
        models: list[ModelInfo] = []

        if self.is_authenticated:
            try:
                response = httpx.get(
                    f"{self._base_url}/models",
                    headers=self._headers(),
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        known = _KNOWN_MODELS.get(mid, {})
                        models.append(ModelInfo(
                            id=mid,
                            name=known.get("name", mid),
                            provider=self._key,
                            context_length=known.get("ctx", 4096),
                            speed_tier=known.get("speed", SpeedTier.MEDIUM),
                            capabilities=[Capability.CHAT, Capability.STREAM],
                            supports_tools=known.get("tools", False),
                            supports_vision=known.get("vision", False),
                            supports_json=known.get("json", False),
                            catalog_source=CatalogSource.LIVE,
                        ))
                    if models:
                        self._catalog_source = CatalogSource.LIVE
                        self._is_reachable = True
                elif response.status_code == 401:
                    self._is_reachable = True
            except Exception as exc:
                self._is_reachable = False
                logger.error(f"Failed to fetch models: {exc}")

        # If API returned nothing, fall back to known models
        if not models:
            self._catalog_source = CatalogSource.FALLBACK
            for mid, known in _KNOWN_MODELS.items():
                if self._key in known.get("providers", []) or self._key == "openai":
                    models.append(ModelInfo(
                        id=mid,
                        name=known["name"],
                        provider=self._key,
                        context_length=known.get("ctx", 4096),
                        speed_tier=known.get("speed", SpeedTier.MEDIUM),
                        capabilities=[Capability.CHAT, Capability.STREAM],
                        supports_tools=known.get("tools", False),
                        supports_vision=known.get("vision", False),
                        supports_json=known.get("json", False),
                        catalog_source=CatalogSource.FALLBACK,
                    ))

        self._models = models
        return models

    def chat(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> ChatResponse:
        """Non-streaming chat completion."""
        self.check_privacy_policy()
        opts = options or ChatOptions()
        httpx = self._get_client()
        start = time.time()

        payload = {
            "model": "",  # Set below
            "messages": [m.to_dict() for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "top_p": opts.top_p,
        }
        if opts.stop:
            payload["stop"] = opts.stop
        if opts.tools:
            payload["tools"] = opts.tools
            payload["tool_choice"] = "auto"
        if opts.json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Use requested model, first available, or default
        models = self.list_models()
        if getattr(opts, "model", None):
            payload["model"] = opts.model
        elif models:
            payload["model"] = models[0].id
        else:
            payload["model"] = "gpt-4o-mini"

        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            choice = data.get("choices", [{}])[0]
            text = choice.get("message", {}).get("content", "")
            tool_calls = choice.get("message", {}).get("tool_calls")
            usage = data.get("usage", {})
            latency = (time.time() - start) * 1000

            return ChatResponse(
                text=text,
                model_id=data.get("model", ""),
                provider=self._key,
                tokens_used=usage.get("total_tokens", 0),
                latency_ms=round(latency, 1),
                finish_reason=choice.get("finish_reason", "stop"),
                tool_calls=tool_calls,
            )
        except Exception as exc:
            logger.error(f"Chat completion failed: {exc}")
            raise RuntimeError(f"Chat completion failed: {exc}") from exc

    def stream(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> Iterator[str]:
        """Stream chat completion tokens."""
        self.check_privacy_policy()
        opts = options or ChatOptions()
        httpx = self._get_client()

        payload = {
            "model": "",
            "messages": [m.to_dict() for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "top_p": opts.top_p,
            "stream": True,
        }
        if opts.stop:
            payload["stop"] = opts.stop
        if opts.tools:
            payload["tools"] = opts.tools
        if opts.json_mode:
            payload["response_format"] = {"type": "json_object"}

        models = self.list_models()
        if getattr(opts, "model", None):
            payload["model"] = opts.model
        elif models:
            payload["model"] = models[0].id
        else:
            payload["model"] = "gpt-4o-mini"

        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except (json.JSONDecodeError, IndexError):
                            continue
        except Exception as exc:
            logger.error(f"Streaming failed: {exc}")
            raise RuntimeError(f"Streaming failed: {exc}") from exc
