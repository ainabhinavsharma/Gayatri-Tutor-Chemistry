"""Gayatri AI — Web Prompt Defense (P11-T05).

Sanitizes retrieved web content as untrusted data to prevent prompt injection attacks.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("gayatri.research.defense")

# Dangerous patterns that attempt to override system prompts or modes
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"\[SYSTEM\s+DIRECTIVE.*?\]", re.I | re.DOTALL),
    re.compile(r"Ignore previous instructions", re.I),
    re.compile(r"You are now a", re.I),
    re.compile(r"Switch mode to", re.I),
    re.compile(r"<\s*system\s*>", re.I),
]


class WebPromptDefense:
    """Sanitizes untrusted web content before prompt injection."""

    @staticmethod
    def sanitize(web_text: str) -> str:
        """Sanitize raw web text by removing prompt injection attempts."""
        if not web_text:
            return ""

        cleaned = web_text
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(cleaned):
                logger.warning("WebPromptDefense: prompt injection attempt stripped from web text")
                cleaned = pattern.sub("[FILTERED PROMPT OVERRIDE]", cleaned)

        # Cap text length to prevent context explosion
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "... [truncated]"

        return cleaned
