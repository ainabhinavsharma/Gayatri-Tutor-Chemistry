"""Legacy agent compatibility module — routes legacy agent calls to core providers."""

from __future__ import annotations

import logging
from typing import Iterator

from core.providers.local import LocalModelError, LocalProvider

logger = logging.getLogger("gayatri.legacy")


def _build_messages(
    system_prompt: str,
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build a list of message dicts for local model chat inference."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        for msg in history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": str(msg["role"]), "content": str(msg["content"])})
    messages.append({"role": "user", "content": user_message})
    return messages


def _get_tutor_context(context=None) -> str:
    """Extract context information string for tutor prompt rendering."""
    if context is None:
        return ""
    if isinstance(context, str):
        return context
    if isinstance(context, dict):
        topic = context.get("topic", "")
        domain = context.get("domain", "")
        concept = context.get("active_concept_id", "")
        mastery = context.get("mastery", "")
        parts = []
        if domain:
            parts.append(f"Domain: {domain}")
        if topic:
            parts.append(f"Topic: {topic}")
        if concept:
            parts.append(f"Active Concept: {concept}")
        if mastery:
            parts.append(f"Mastery: {mastery}")
        return "\n".join(parts)
    return str(context)


def _local_chat_stream(
    messages: list[dict[str, str]],
    max_tokens: int = 400,
) -> Iterator[str]:
    """Stream chat responses via LocalProvider or yield fallback message."""
    try:
        if LocalProvider.is_available():
            yield from LocalProvider.chat_stream(messages, max_tokens=max_tokens)
        else:
            fallback = (
                "Welcome to Gayatri AI Tutor! Local model is currently operating in offline/demo mode. "
                "To enable full local LLM responses, ensure the GGUF model file is downloaded in `GayatriAI\\models\\gayatri`."
            )
            yield fallback
    except LocalModelError as exc:
        logger.warning(f"LocalProvider unavailable in _local_chat_stream: {exc}")
        yield f"Gayatri AI Tutor: {exc.message}"
    except Exception as exc:
        logger.error(f"Unexpected error in _local_chat_stream: {exc}")
        yield "Gayatri AI Tutor: An error occurred while generating the response."
