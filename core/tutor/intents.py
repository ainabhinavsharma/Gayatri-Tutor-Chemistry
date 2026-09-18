"""Gayatri AI — Tutor Intent Classifier.

Classifies incoming student queries into internal tutoring intents without dynamic multi-agent delegation.
"""
from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger("gayatri.tutor.intents")


class TutorIntent(str, Enum):
    LEARN = "learn"
    EXPLAIN = "explain"
    SOLVE = "solve"
    PRACTICE = "practice"
    TEST = "test"
    REVIEW = "review"
    CLARIFY = "clarify"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    UNKNOWN = "unknown"


# Keyword rules for fast, deterministic intent classification
INTENT_PATTERNS: list[tuple[TutorIntent, re.Pattern]] = [
    (TutorIntent.SOLVE, re.compile(r"\b(solve|calculate|compute|find|determine|numerical|equal to|how many joules|value of)\b", re.I)),
    (TutorIntent.PRACTICE, re.compile(r"\b(practice|exercise|problems|questions|quiz me|give me a problem)\b", re.I)),
    (TutorIntent.TEST, re.compile(r"\b(test|assess|exam|evaluation|grade)\b", re.I)),
    (TutorIntent.SUMMARIZE, re.compile(r"\b(summarize|summary|overview|brief|key points|in short)\b", re.I)),
    (TutorIntent.COMPARE, re.compile(r"\b(compare|difference|versus|vs|differentiate|distinguish)\b", re.I)),
    (TutorIntent.CLARIFY, re.compile(r"\b(why|how come|what if|confused|dont understand|explain why|clarify)\b", re.I)),
    (TutorIntent.REVIEW, re.compile(r"\b(review|revise|revision|recap)\b", re.I)),
    (TutorIntent.EXPLAIN, re.compile(r"\b(explain|what is|define|tell me about|concept|meaning of)\b", re.I)),
    (TutorIntent.LEARN, re.compile(r"\b(learn|teach|study|start|begin|guide me)\b", re.I)),
]


class TutorIntentClassifier:
    """Classifies user messages into internal tutoring intents."""

    @staticmethod
    def classify(user_message: str) -> TutorIntent:
        """Classify user intent using regex pattern matching."""
        if not user_message or not user_message.strip():
            return TutorIntent.UNKNOWN

        text = user_message.strip()
        for intent, pattern in INTENT_PATTERNS:
            if pattern.search(text):
                logger.info(f"Classified intent: {intent.value} for query '{text[:30]}...'")
                return intent

        logger.info(f"Intent unclassified for query '{text[:30]}...', defaulting to EXPLAIN")
        return TutorIntent.EXPLAIN
