"""Gayatri AI — Concept-Aware RAG Retriever & Evidence Control (Phase 7).

Performs similarity queries combined with active concept context (P7-T01),
enforces source provenance priority (P7-T02 & P7-T03), and provides observable RAG status (P7-T04).
"""
from __future__ import annotations

import logging
from typing import Optional

from core.rag.schema import ConfidenceLevel, RAGContext, RAGStatus, RetrievalResult
from core.rag.store import RAGStore

logger = logging.getLogger("gayatri.rag.retriever")

# Policy thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.45
MEDIUM_CONFIDENCE_THRESHOLD = 0.20

SOURCE_PRIORITY_WEIGHTS = {
    "NCERT": 10.0,
    "TRUSTED_CURRICULUM": 5.0,
    "FALLBACK": 1.0,
}


class NCERTRetriever:
    """Concept-aware retriever for querying NCERT knowledge with evidence priority and error observation."""

    def __init__(self, store: Optional[RAGStore] = None):
        self.store = store or RAGStore()

    def retrieve(self, query: str, top_k: int = 3) -> RAGContext:
        """Legacy retriever wrapper."""
        return self.retrieve_concept_aware(query=query, top_k=top_k)

    def retrieve_concept_aware(
        self,
        query: str,
        domain: str = "",
        chapter: str = "",
        topic: str = "",
        concept_id: str = "",
        top_k: int = 3,
    ) -> RAGContext:
        """Concept-aware retrieval combining query text and curriculum context (P7-T01)."""
        if not query or not query.strip():
            return RAGContext(
                query=query,
                results=[],
                confidence=ConfidenceLevel.LOW,
                status=RAGStatus.RAG_STATUS_EMPTY,
            )

        # Build enriched context query
        context_parts = [p for p in [domain, chapter, topic, concept_id] if p]
        enriched_query = f"{query} {' '.join(context_parts)}".strip()

        try:
            matches = self.store.search_similar(enriched_query, top_k=top_k * 2)
        except Exception as e:
            logger.error(f"RAG Store search error: {e}")
            return RAGContext(
                query=query,
                results=[],
                confidence=ConfidenceLevel.LOW,
                status=RAGStatus.RAG_STATUS_ERROR,
                error_message=str(e),
            )

        if not matches:
            return RAGContext(
                query=query,
                results=[],
                confidence=ConfidenceLevel.LOW,
                status=RAGStatus.RAG_STATUS_EMPTY,
            )

        # Process and rank results by source priority (NCERT > TRUSTED > FALLBACK) & score (P7-T03)
        results: list[RetrievalResult] = []
        for chunk, score in matches:
            if score >= HIGH_CONFIDENCE_THRESHOLD:
                conf = ConfidenceLevel.HIGH
            elif score >= MEDIUM_CONFIDENCE_THRESHOLD:
                conf = ConfidenceLevel.MEDIUM
            else:
                conf = ConfidenceLevel.LOW

            results.append(RetrievalResult(chunk=chunk, score=score, confidence=conf))

        # Sort by (source_priority_weight, similarity_score) descending
        results.sort(
            key=lambda r: (
                SOURCE_PRIORITY_WEIGHTS.get(getattr(r.chunk, "provenance_type", "NCERT"), 1.0),
                r.score,
            ),
            reverse=True,
        )
        final_results = results[:top_k]

        top_score = final_results[0].score if final_results else 0.0
        if top_score >= HIGH_CONFIDENCE_THRESHOLD:
            overall_confidence = ConfidenceLevel.HIGH
        elif top_score >= MEDIUM_CONFIDENCE_THRESHOLD:
            overall_confidence = ConfidenceLevel.MEDIUM
        else:
            overall_confidence = ConfidenceLevel.LOW

        logger.info(
            f"Concept-aware RAG for '{query[:30]}...' (concept={concept_id}): "
            f"{len(final_results)} chunks, top_score={top_score:.4f}, confidence={overall_confidence.value}"
        )

        return RAGContext(
            query=query,
            results=final_results,
            confidence=overall_confidence,
            status=RAGStatus.RAG_STATUS_OK,
        )


_global_retriever: Optional[NCERTRetriever] = None


def get_ncert_retriever() -> NCERTRetriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = NCERTRetriever()
    return _global_retriever
