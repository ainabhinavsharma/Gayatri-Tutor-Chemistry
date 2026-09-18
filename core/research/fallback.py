"""Gayatri AI — Research Fallback Evaluator (P11-T02).

Evaluates whether a query meets criteria for web research fallback:
- Local RAG confidence is LOW
- Policy allows web search (privacy_mode == 'cloud_allowed')
- Non-empty query
"""
from __future__ import annotations

import logging

from core.rag.schema import ConfidenceLevel
from core.research.policy import ResearchPolicy

logger = logging.getLogger("gayatri.research.fallback")


class ResearchFallbackEvaluator:
    """Evaluates whether to trigger controlled web fallback."""

    @staticmethod
    def should_fallback(
        rag_confidence: ConfidenceLevel,
        policy: ResearchPolicy,
        user_message: str,
    ) -> bool:
        """Return True if query requires web fallback under policy."""
        if not user_message or not user_message.strip():
            return False

        if not policy.enabled:
            logger.info("Web research fallback skipped: policy disabled (local_only)")
            return False

        if rag_confidence != ConfidenceLevel.LOW:
            logger.info(f"Web research fallback skipped: RAG confidence is {rag_confidence.value}")
            return False

        logger.info("Web research fallback TRIGGERED: low RAG confidence + cloud allowed policy")
        return True
