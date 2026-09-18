"""Gayatri AI — RAG Retriever & Confidence Evaluator.

Performs similarity queries, applies quality thresholds, and produces RAGContext.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from core.rag.schema import ConfidenceLevel, RAGContext, RetrievalResult
from core.rag.store import RAGStore

logger = logging.getLogger("gayatri.rag.retriever")

# Policy thresholds (P5-T05)
HIGH_CONFIDENCE_THRESHOLD = 0.45
MEDIUM_CONFIDENCE_THRESHOLD = 0.20


class NCERTRetriever:
    """Retriever for querying NCERT knowledge and evaluating confidence."""

    def __init__(self, store: Optional[RAGStore] = None):
        self.store = store or RAGStore()

    def retrieve(self, query: str, top_k: int = 3) -> RAGContext:
        """Query RAGStore, evaluate confidence score, and return a structured RAGContext."""
        if not query or not query.strip():
            return RAGContext(query=query, results=[], confidence=ConfidenceLevel.LOW)

        matches = self.store.search_similar(query, top_k=top_k)
        if not matches:
            return RAGContext(query=query, results=[], confidence=ConfidenceLevel.LOW)

        top_score = matches[0][1]

        # Determine confidence level
        if top_score >= HIGH_CONFIDENCE_THRESHOLD:
            overall_confidence = ConfidenceLevel.HIGH
        elif top_score >= MEDIUM_CONFIDENCE_THRESHOLD:
            overall_confidence = ConfidenceLevel.MEDIUM
        else:
            overall_confidence = ConfidenceLevel.LOW

        results: list[RetrievalResult] = []
        for chunk, score in matches:
            if score >= HIGH_CONFIDENCE_THRESHOLD:
                conf = ConfidenceLevel.HIGH
            elif score >= MEDIUM_CONFIDENCE_THRESHOLD:
                conf = ConfidenceLevel.MEDIUM
            else:
                conf = ConfidenceLevel.LOW

            results.append(RetrievalResult(chunk=chunk, score=score, confidence=conf))

        logger.info(
            f"RAG Retrieval for '{query[:30]}...': {len(results)} chunks, "
            f"top_score={top_score:.4f}, confidence={overall_confidence.value}"
        )

        return RAGContext(
            query=query,
            results=results,
            confidence=overall_confidence,
        )


_global_retriever: Optional[NCERTRetriever] = None


def get_ncert_retriever() -> NCERTRetriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = NCERTRetriever()
    return _global_retriever
