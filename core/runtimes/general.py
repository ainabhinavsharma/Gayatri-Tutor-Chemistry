"""Gayatri AI — General Assistant Runtime.

Deterministic execution block for GENERAL_ASSISTANT mode.
Provides general conversation, writing, drafting, summarization, brainstorming,
and general reasoning capabilities via prompt contracts and unified InferenceService.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from core.settings import get_settings
from core.prompts.loader import get_prompt_loader
from core.inference.service import get_inference_service

logger = logging.getLogger("gayatri.runtimes.general")

# Regex for detecting chemistry tutoring / learning requests inside General Assistant
CHEMISTRY_TUTORING_PATTERNS = [
    re.compile(r"\b(teach me chemistry|ncert chemistry|learn thermodynamics|hess'?s law|gibbs free energy|balance chemical equation|chemistry test|chemistry quiz)\b", re.I),
    re.compile(r"\b(chemistry tutor|grade my chemistry|chemistry mastery|s-block elements|p-block elements)\b", re.I),
]


def _detect_chemistry_tutoring_request(user_message: str) -> bool:
    """Detect if the user is asking for specialized chemistry tutoring inside General Assistant mode."""
    if not user_message:
        return False
    text = user_message.strip()
    for pattern in CHEMISTRY_TUTORING_PATTERNS:
        if pattern.search(text):
            logger.info(f"Chemistry tutoring request detected in General Assistant: '{text[:30]}...'")
            return True
    return False


def _build_general_system_prompt(is_chemistry_redirect: bool = False) -> str:
    """Build the General Assistant system prompt using versioned prompt contract."""
    template = get_prompt_loader().load_prompt("general_assistant_system_v1.txt")

    redirect_block = ""
    if is_chemistry_redirect:
        redirect_block = (
            "\n[NOTICE: MODE BOUNDARY]\n"
            "The user's query appears to be a specialized Chemistry tutoring or assessment request. "
            "Politely answer briefly if possible, and inform the user that for adaptive, step-by-step "
            "NCERT Chemistry tutoring, interactive quizzes, and topic mastery tracking, they should switch "
            "to 'Chemistry Tutor' mode."
        )

    if template:
        return template.format(redirect_block=redirect_block)

    # Fallback if contract template is unreadable
    base_prompt = get_settings().get(
        "system_prompt",
        "You are Gayatri AI, a helpful, versatile learning and general-purpose AI assistant."
    )
    return f"{base_prompt}\n{redirect_block}"


class GeneralAssistantRuntime:
    """General Assistant runtime — general AI capabilities with Prompt Contracts and InferenceService."""

    def stream(self, user_message: str, context):
        """Stream a response for a general assistant turn."""
        try:
            from legacy.agents.default_agents import _build_messages

            is_chem_req = _detect_chemistry_tutoring_request(user_message)
            system = _build_general_system_prompt(is_chemistry_redirect=is_chem_req)

            msgs = _build_messages(
                system,
                user_message,
                getattr(context, "history", None),
            )
            return get_inference_service().stream_chat(msgs, max_tokens=800)
        except Exception as exc:
            logger.error(f"GeneralAssistantRuntime.stream error: {exc}")
            raise
