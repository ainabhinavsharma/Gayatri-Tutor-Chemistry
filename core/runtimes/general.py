"""Gayatri AI — General Assistant Runtime.

Deterministic execution block for GENERAL_ASSISTANT mode.
Provides general conversation, writing, drafting, summarization, brainstorming,
and general reasoning capabilities without legacy agent routing or chemistry mastery side-effects.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from core.settings import get_settings

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
    """Build the General Assistant system prompt."""
    base_prompt = get_settings().get(
        "system_prompt",
        "You are Gayatri AI, a helpful, versatile learning and general-purpose AI assistant."
    )

    capabilities_block = """
Your supported core capabilities include:
- Conversation & General Reasoning: Answer questions thoughtfully and accurately.
- Writing & Editing: Draft, rewrite, polish, shorten, expand, or professionalize text.
- Summarization: Create bullet points, key takeaways, or concise executive summaries.
- Brainstorming & Planning: Generate creative ideas, outlines, pros/cons lists, and step-by-step plans.

Guidelines:
- Remain helpful, clear, and local-first.
- Do not pretend to be a specialized Chemistry Tutor.
- Do not invoke legacy agents or hidden router modes.
"""

    if is_chemistry_redirect:
        redirect_block = (
            "\n[NOTICE: MODE BOUNDARY]\n"
            "The user's query appears to be a specialized Chemistry tutoring or assessment request. "
            "Politely answer briefly if possible, and inform the user that for adaptive, step-by-step "
            "NCERT Chemistry tutoring, interactive quizzes, and topic mastery tracking, they should switch "
            "to 'Chemistry Tutor' mode."
        )
        return f"{base_prompt}\n{capabilities_block}\n{redirect_block}"

    return f"{base_prompt}\n{capabilities_block}"


class GeneralAssistantRuntime:
    """General Assistant runtime — general AI capabilities without agent routing."""

    def stream(self, user_message: str, context):
        """Stream a response for a general assistant turn."""
        try:
            from legacy.agents.default_agents import _build_messages, _local_chat_stream

            is_chem_req = _detect_chemistry_tutoring_request(user_message)
            system = _build_general_system_prompt(is_chemistry_redirect=is_chem_req)

            msgs = _build_messages(
                system,
                user_message,
                getattr(context, "history", None),
            )
            return _local_chat_stream(msgs, max_tokens=400)
        except Exception as exc:
            logger.error(f"GeneralAssistantRuntime.stream error: {exc}")
            raise
