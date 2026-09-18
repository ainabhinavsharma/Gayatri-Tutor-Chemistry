"""Gayatri AI — Anthropic Claude provider.

Uses the Messages API (claude-sonnet, claude-opus, claude-haiku).
"""

from __future__ import annotations

import json
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

logger = logging.getLogger("gayatri.providers.anthropic")

_KNOWN_MODELS: dict[str, dict] = {
    "claude-sonnet-4-20250514": {"name": "Claude Sonnet 4", "ctx": 200000, "speed": SpeedTier.MEDIUM, "tools": True, "vision": True, "json": False},
    "claude-opus-4-20250514": {"name": "Claude Opus 4", "ctx": 200000, "speed": SpeedTier.SLOW, "tools": True, "vision": True, "json": False},
    "claude-3-5-sonnet-20241022": {"name": "Claude 3.5 Sonnet", "ctx": 200000, "speed": SpeedTier.MEDIUM, "tools": True, "vision": True, "json": False},
    "claude-3-5-haiku-20241022": {"name": "Claude 3.5 Haiku", "ctx": 200000, "speed": SpeedTier.FAST, "tools": True, "vision": True, "json": False},
    "claude-3-opus-20240229": {"name": "Claude 3 Opus", "ctx": 200000, "speed": SpeedTier.SLOW, "tools": True, "vision": True, "json": False},
    "claude-3-haiku-20240307": {"name": "Claude 3 Haiku", "ctx": 200000, "speed": SpeedTier.FAST, "tools": True, "vision": True, "json": False},
}


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider.

    Uses the Messages API: https://docs.anthropic.com/claude/reference/messages
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._name = "Anthropic"
        self._key = "anthropic"
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
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def validate_key(self) -> tuple[bool, str]:
        """Validate key with a minimal messages API call."""
        if not self.is_authenticated:
            self._is_reachable = False
            return False, "API key not configured"

        try:
            import httpx
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers=self._headers(),
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
                timeout=15.0,
            )
            if response.status_code == 200:
                self._is_reachable = True
                return True, "OK"
            elif response.status_code == 401:
                self._is_reachable = True
                return False, "Invalid API key"
            else:
                self._is_reachable = True
                body = response.text[:200]
                return False, f"HTTP {response.status_code}: {body}"
        except ImportError:
            return False, "httpx not installed"
        except Exception as exc:
            self._is_reachable = False
            from core.errors import sanitize_message
            return False, sanitize_message(str(exc))[:200]

    def list_models(self) -> list[ModelInfo]:
        """Return models from Anthropic API or fallback catalog."""
        if self._models is not None:
            return self._models

        self._models = []
        if self.is_authenticated:
            try:
                import httpx
                response = httpx.get(
                    "https://api.anthropic.com/v1/models",
                    headers=self._headers(),
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    for m in data.get("data", []):
                        mid = m.get("id", "")
                        meta = _KNOWN_MODELS.get(mid, {})
                        self._models.append(ModelInfo(
                            id=mid,
                            name=meta.get("name", m.get("display_name", mid)),
                            provider="anthropic",
                            context_length=meta.get("ctx", 200000),
                            speed_tier=meta.get("speed", SpeedTier.MEDIUM),
                            capabilities=[Capability.CHAT, Capability.STREAM, Capability.SYSTEM_PROMPT],
                            supports_tools=meta.get("tools", True),
                            supports_vision=meta.get("vision", True),
                            supports_json=False,
                            catalog_source=CatalogSource.LIVE,
                        ))
                    if self._models:
                        self._catalog_source = CatalogSource.LIVE
                        self._is_reachable = True
                elif response.status_code == 401:
                    self._is_reachable = True
            except Exception as exc:
                self._is_reachable = False
                logger.debug(f"Anthropic live models fetch failed: {exc}")

        # Fallback to known models
        if not self._models:
            self._catalog_source = CatalogSource.FALLBACK
            for mid, meta in _KNOWN_MODELS.items():
                self._models.append(ModelInfo(
                    id=mid,
                    name=meta["name"],
                    provider="anthropic",
                    context_length=meta.get("ctx", 200000),
                    speed_tier=meta.get("speed", SpeedTier.MEDIUM),
                    capabilities=[Capability.CHAT, Capability.STREAM, Capability.SYSTEM_PROMPT],
                    supports_tools=meta.get("tools", False),
                    supports_vision=meta.get("vision", False),
                    supports_json=False,
                    catalog_source=CatalogSource.FALLBACK,
                ))
        return self._models

    def _convert_messages(self, messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
        """Convert ChatMessages to Anthropic format.

        Anthropic separates system prompt. Returns (system_prompt, messages_list).
        Also converts assistant tool_calls and tool results.
        """
        system_prompt = None
        result = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role == "assistant" and msg.tool_calls:
                # Tool call response
                for tc in msg.tool_calls:
                    result.append({
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": tc.get("id", ""),
                                "name": tc.get("function", {}).get("name", ""),
                                "input": tc.get("function", {}).get("arguments", {}),
                            }
                        ],
                    })
            elif msg.role == "tool":
                result.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                })
            else:
                result.append({"role": msg.role, "content": msg.content})

        return system_prompt, result

    def chat(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> ChatResponse:
        """Non-streaming chat completion via Messages API."""
        self.check_privacy_policy()
        opts = options or ChatOptions()
        import httpx
        start = time.time()

        system_prompt, anthropic_msgs = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": "claude-3-5-sonnet-20241022",  # default
            "max_tokens": opts.max_tokens,
            "messages": anthropic_msgs,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if opts.temperature > 0:
            payload["temperature"] = opts.temperature
        if opts.top_p < 1.0:
            payload["top_p"] = opts.top_p
        if opts.stop:
            payload["stop_sequences"] = opts.stop
        if opts.tools:
            payload["tools"] = opts.tools
        if opts.json_mode:
            json_instruction = "Respond strictly with valid JSON. Do not include markdown formatting, backticks, or commentary."
            if "system" in payload:
                payload["system"] = f"{payload['system']}\n\n{json_instruction}"
            else:
                payload["system"] = json_instruction

        # Pick requested model or best available
        models = self.list_models()
        if getattr(opts, "model", None):
            payload["model"] = opts.model
        elif models:
            payload["model"] = models[0].id

        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers=self._headers(),
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("content", [])
            text = ""
            tool_calls = None
            for block in content:
                if block.get("type") == "text":
                    text += block.get("text", "")
                elif block.get("type") == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    })

            usage = data.get("usage", {})
            latency = (time.time() - start) * 1000

            return ChatResponse(
                text=text,
                model_id=data.get("model", ""),
                provider="anthropic",
                tokens_used=usage.get("output_tokens", 0) + usage.get("input_tokens", 0),
                latency_ms=round(latency, 1),
                finish_reason=data.get("stop_reason", "stop"),
                tool_calls=tool_calls,
            )
        except Exception as exc:
            logger.error(f"Anthropic chat failed: {exc}")
            raise RuntimeError(f"Anthropic chat failed: {exc}") from exc

    def stream(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> Iterator[str]:
        """Stream chat completion via Messages API."""
        self.check_privacy_policy()
        opts = options or ChatOptions()
        import json

        import httpx
        
        system_prompt, anthropic_msgs = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": opts.max_tokens,
            "messages": anthropic_msgs,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if opts.temperature > 0:
            payload["temperature"] = opts.temperature
        if opts.tools:
            payload["tools"] = opts.tools
        if opts.json_mode:
            json_instruction = "Respond strictly with valid JSON. Do not include markdown formatting, backticks, or commentary."
            if "system" in payload:
                payload["system"] = f"{payload['system']}\n\n{json_instruction}"
            else:
                payload["system"] = json_instruction

        models = self.list_models()
        if getattr(opts, "model", None):
            payload["model"] = opts.model
        elif models:
            payload["model"] = models[0].id

        try:
            with httpx.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers=self._headers(),
                json=payload,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    yield text
                        except (json.JSONDecodeError, KeyError):
                            continue
        except Exception as exc:
            logger.error(f"Anthropic stream failed: {exc}")
            raise RuntimeError(f"Anthropic stream failed: {exc}") from exc

    def supports_tools(self) -> bool:
        return True

    def supports_vision(self) -> bool:
        return True

    def supports_json(self) -> bool:
        return False
