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
    "APPROVED_CURRICULUM": 5.0,
    "TRUSTED_CURRICULUM": 5.0,
    "FALLBACK": 1.0,
}


class NCERTRetriever:
    """Concept-aware retriever for querying NCERT knowledge with evidence priority and error observation (Section 19)."""

    def __init__(self, store: Optional[RAGStore] = None):
        self.store = store or RAGStore()
        if store is None:
            try:
                from core.rag.seeder import seed_ncert_rag
                seed_ncert_rag(self.store)
            except Exception as exc:
                logger.warning(f"Could not auto-seed RAGStore: {exc}")

    def retrieve(self, query: str, top_k: int = 3) -> RAGContext:
        """Legacy retriever wrapper."""
        return self.retrieve_concept_aware(query=query, top_k=top_k)

    def retrieve_concept_aware(
        self,
        query: str = "",
        domain: str = "",
        chapter: str = "",
        topic: str = "",
        concept_id: str = "",
        learning_objective: str = "",
        top_k: int = 3,
        question: str = "",
        concept: str = "",
    ) -> RAGContext:
        """Multi-factor retrieval combining question, domain, chapter, topic, concept, and learning objective (Section 19)."""
        q = (query or question).strip()
        cid = concept_id or concept
        if not q:
            return RAGContext(
                query=q,
                results=[],
                confidence=ConfidenceLevel.LOW,
                status=RAGStatus.RAG_EMPTY,
            )

        # Build enriched context query from all 6 factors (Section 19)
        context_parts = [p for p in [domain, chapter, topic, cid, learning_objective] if p]
        enriched_query = f"{q} {' '.join(context_parts)}".strip()

        try:
            matches = self.store.search_similar(enriched_query, top_k=max(1, top_k * 2))
        except Exception as e:
            logger.error(f"RAG Store search error: {e}")
            return RAGContext(
                query=q,
                results=[],
                confidence=ConfidenceLevel.LOW,
                status=RAGStatus.RAG_ERROR,
                error_message=str(e),
            )

        if not matches:
            return RAGContext(
                query=q,
                results=[],
                confidence=ConfidenceLevel.LOW,
                status=RAGStatus.RAG_EMPTY,
            )

        # Process and rank results by source priority (NCERT > APPROVED_CURRICULUM > FALLBACK) & score (Section 19)
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
            f"Concept-aware RAG for '{q[:30]}...' (concept={cid}): "
            f"{len(final_results)} chunks, top_score={top_score:.4f}, confidence={overall_confidence.value}"
        )

        return RAGContext(
            query=q,
            results=final_results,
            confidence=overall_confidence,
            status=RAGStatus.RAG_OK,
        )


_global_retriever: Optional[NCERTRetriever] = None


def get_ncert_retriever() -> NCERTRetriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = NCERTRetriever()
    return _global_retriever
