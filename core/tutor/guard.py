"""Gayatri AI — Out-of-Domain Guard (P6-T10).

Detects non-chemistry requests (coding, general math, python, arbitrary internet topics)
and produces polite redirection prompts.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("gayatri.tutor.guard")

# Regex patterns for non-chemistry requests
NON_CHEMISTRY_PATTERNS = [
    re.compile(r"\b(write python|code|def |class |import os|javascript|html|css|sql query)\b", re.I),
    re.compile(r"\b(who won the|movie|weather|recipe for|capital of|stock market)\b", re.I),
]


class OutOfDomainGuard:
    """Guards Chemistry Tutor runtime against non-chemistry queries."""

    @staticmethod
    def is_out_of_domain(user_message: str) -> bool:
        """Check if user message matches non-chemistry topics."""
        if not user_message:
            return False
        text = user_message.strip()
        for pattern in NON_CHEMISTRY_PATTERNS:
            if pattern.search(text):
                logger.info(f"Out-of-domain query detected: '{text[:30]}...'")
                return True
        return False

    @staticmethod
    def get_redirection_prompt(user_message: str) -> str:
        """Return polite redirection directive."""
        return (
            "[SYSTEM DIRECTIVE: OUT-OF-DOMAIN REDIRECTION]\n"
            "The user asked a non-chemistry question. Politely decline to answer non-chemistry tasks "
            "(such as coding, general trivia, or external topics), and invite them to explore "
            "NCERT Chemistry topics like Thermodynamics or Inorganic Chemistry."
        )
