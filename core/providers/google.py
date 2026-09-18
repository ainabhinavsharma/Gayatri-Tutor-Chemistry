"""Gayatri AI — Google Gemini provider.

Uses the Gemini API: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

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

logger = logging.getLogger("gayatri.providers.google")

_KNOWN_MODELS: dict[str, dict] = {
    "gemini-2.0-flash": {"name": "Gemini 2.0 Flash", "ctx": 1000000, "speed": SpeedTier.FAST, "tools": False, "vision": True, "json": True},
    "gemini-2.0-flash-lite": {"name": "Gemini 2.0 Flash Lite", "ctx": 1000000, "speed": SpeedTier.FAST, "tools": False, "vision": True, "json": True},
    "gemini-1.5-pro": {"name": "Gemini 1.5 Pro", "ctx": 2000000, "speed": SpeedTier.MEDIUM, "tools": False, "vision": True, "json": True},
    "gemini-1.5-flash": {"name": "Gemini 1.5 Flash", "ctx": 1000000, "speed": SpeedTier.FAST, "tools": False, "vision": True, "json": True},
    "gemini-1.0-pro": {"name": "Gemini 1.0 Pro", "ctx": 32000, "speed": SpeedTier.MEDIUM, "tools": False, "vision": False, "json": True},
}


class GoogleProvider(LLMProvider):
    """Google Gemini API provider.

    Uses generateContent endpoint: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._name = "Google"
        self._key = "google"
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
            and self._catalog_source == CatalogSource.LIVE
            and len(self._models or []) > 0
        )

    def _base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta"

    def validate_key(self) -> tuple[bool, str]:
        """Validate key by calling list models endpoint."""
        if not self.is_authenticated:
            self._is_reachable = False
            return False, "API key not configured"

        try:
            import httpx
            response = httpx.get(
                f"{self._base_url()}/models",
                headers={"x-goog-api-key": self._api_key},
                timeout=10.0,
            )
            if response.status_code == 200:
                self._is_reachable = True
                return True, "OK"
            elif response.status_code == 400:
                self._is_reachable = True
                return False, "Invalid API key"
            else:
                self._is_reachable = True
                return False, f"HTTP {response.status_code}"
        except ImportError:
            return False, "httpx not installed"
        except Exception as exc:
            self._is_reachable = False
            from core.errors import sanitize_message
            return False, sanitize_message(str(exc))[:200]

    def list_models(self) -> list[ModelInfo]:
        """Fetch models from Google API, with known model fallbacks."""
        if self._models is not None:
            return self._models

        self._models = []
        if self.is_authenticated:
            try:
                import httpx
                response = httpx.get(
                    f"{self._base_url()}/models",
                    headers={"x-goog-api-key": self._api_key},
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    for m in data.get("models", []):
                        mid = m.get("name", "").replace("models/", "")
                        if "gemini" not in mid.lower():
                            continue
                        known = _KNOWN_MODELS.get(mid, {})
                        self._models.append(ModelInfo(
                            id=mid,
                            name=known.get("name", m.get("displayName", mid)),
                            provider="google",
                            context_length=known.get("ctx", 8192),
                            speed_tier=known.get("speed", SpeedTier.MEDIUM),
                            capabilities=[Capability.CHAT, Capability.STREAM, Capability.SYSTEM_PROMPT],
                            supports_tools=False,
                            supports_vision=known.get("vision", False),
                            supports_json=known.get("json", False),
                            catalog_source=CatalogSource.LIVE,
                        ))
                    if self._models:
                        self._catalog_source = CatalogSource.LIVE
                        self._is_reachable = True
                elif response.status_code == 400:
                    self._is_reachable = True
            except Exception as exc:
                self._is_reachable = False
                logger.error(f"Failed to fetch Google models: {exc}")

        # Fallback to known models if live fetch returned nothing
        if not self._models:
            self._catalog_source = CatalogSource.FALLBACK
            for mid, meta in _KNOWN_MODELS.items():
                self._models.append(ModelInfo(
                    id=mid,
                    name=meta["name"],
                    provider="google",
                    context_length=meta.get("ctx", 8192),
                    speed_tier=meta.get("speed", SpeedTier.MEDIUM),
                    capabilities=[Capability.CHAT, Capability.STREAM, Capability.SYSTEM_PROMPT],
                    supports_tools=False,
                    supports_vision=meta.get("vision", False),
                    supports_json=meta.get("json", False),
                    catalog_source=CatalogSource.FALLBACK,
                ))

        return self._models

    def _convert_messages(self, messages: list[ChatMessage], supports_system: bool = True) -> tuple[str | None, list[dict]]:
        """Convert ChatMessages to Gemini format.

        Gemini uses 'user'/'model' roles. System prompt goes in systemInstruction.
        Returns (system_prompt, contents_list).
        """
        system_prompt = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                if supports_system:
                    system_prompt = msg.content
                else:
                    contents.append({"role": "user", "parts": [{"text": f"[System: {msg.content}]"}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "tool":
                # Gemini doesn't have native tool_result — append as user message
                contents.append({"role": "user", "parts": [{"text": f"[Tool result: {msg.content}]"}]})

        return system_prompt, contents

    def chat(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> ChatResponse:
        """Non-streaming chat completion."""
        self.check_privacy_policy()
        opts = options or ChatOptions()

        import httpx
        start = time.time()

        system_prompt, contents = self._convert_messages(messages)
        models = self.list_models()
        model_id = getattr(opts, "model", None) or (models[0].id if models else "gemini-1.5-flash")

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": opts.temperature,
                "maxOutputTokens": opts.max_tokens,
                "topP": opts.top_p,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if opts.stop:
            payload["generationConfig"]["stopSequences"] = opts.stop
        if opts.json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        try:
            response = httpx.post(
                f"{self._base_url()}/models/{model_id}:generateContent",
                headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No candidates in response")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

            usage = data.get("usageMetadata", {})
            latency = (time.time() - start) * 1000

            return ChatResponse(
                text=text,
                model_id=model_id,
                provider="google",
                tokens_used=usage.get("totalTokenCount", 0),
                latency_ms=round(latency, 1),
                finish_reason=candidates[0].get("finishReason", "STOP"),
            )
        except Exception as exc:
            from core.errors import sanitize_message
            clean_msg = sanitize_message(str(exc))
            logger.error(f"Google chat failed: {clean_msg}")
            raise RuntimeError(f"Google chat failed: {clean_msg}") from exc

    def stream(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> Iterator[str]:
        """Stream chat completion."""
        self.check_privacy_policy()
        opts = options or ChatOptions()
        import httpx

        system_prompt, contents = self._convert_messages(messages)
        models = self.list_models()
        model_id = getattr(opts, "model", None) or (models[0].id if models else "gemini-1.5-flash")

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": opts.temperature,
                "maxOutputTokens": opts.max_tokens,
                "topP": opts.top_p,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            with httpx.stream(
                "POST",
                f"{self._base_url()}/models/{model_id}:streamGenerateContent?alt=sse",
                headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
                json=payload,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            import json
                            chunk = json.loads(raw)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    text = p.get("text", "")
                                    if text:
                                        yield text
                        except (ImportError, Exception):
                            continue
        except Exception as exc:
            from core.errors import sanitize_message
            clean_msg = sanitize_message(str(exc))
            logger.error(f"Google stream failed: {clean_msg}")
            raise RuntimeError(f"Google stream failed: {clean_msg}") from exc

    def supports_tools(self) -> bool:
        return False

    def supports_vision(self) -> bool:
        return True

    def supports_json(self) -> bool:
        return True
