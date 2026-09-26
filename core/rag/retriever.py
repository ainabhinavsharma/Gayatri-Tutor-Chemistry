"""Gayatri AI — RAG 2.0: Hybrid Retrieval Engine (Phase 4).

Combines Vector Similarity + BM25 Lexical Keyword Search + Metadata Filters
using Reciprocal Rank Fusion (RRF) and generates EvidenceCard representations.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any

from core.rag.schema import ConfidenceLevel, DocumentChunk, EvidenceCard, RAGContext, RAGStatus, RetrievalResult
from core.rag.store import RAGStore

logger = logging.getLogger("gayatri.rag.retriever")

# Policy thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.45
MEDIUM_CONFIDENCE_THRESHOLD = 0.20
RRF_K_CONSTANT = 60

SOURCE_PRIORITY_WEIGHTS = {
    "NCERT": 10.0,
    "APPROVED_CURRICULUM": 5.0,
    "TRUSTED_CURRICULUM": 5.0,
    "FALLBACK": 1.0,
}


class BM25LexicalScorer:
    """Simple, fast in-memory BM25 lexical keyword scorer."""

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-\+]+\b", text)]

    @classmethod
    def score_chunk(cls, query: str, chunk_text: str) -> float:
        q_tokens = set(cls.tokenize(query))
        c_tokens = cls.tokenize(chunk_text)
        if not q_tokens or not c_tokens:
            return 0.0

        score = 0.0
        c_len = len(c_tokens)
        for qt in q_tokens:
            tf = c_tokens.count(qt)
            if tf > 0:
                # BM25 term weighting component
                idf = math.log((100 + 1) / (1 + 1))
                tf_score = (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * (c_len / 50)))
                score += idf * tf_score

        return round(score, 4)


class NCERTRetriever:
    """Hybrid Retriever combining Vector Search, BM25 Lexical Search, and RRF Reranking."""

    def __init__(self, store: RAGStore | None = None):
        self.store = store or RAGStore()
        if store is None:
            try:
                from core.rag.seeder import seed_ncert_rag
                seed_ncert_rag(self.store)
            except Exception as exc:
                logger.warning(f"Could not auto-seed RAGStore: {exc}")

    def retrieve(self, query: str, top_k: int = 3) -> RAGContext:
        """Legacy retriever wrapper."""
        return self.retrieve_hybrid(query=query, top_k=top_k)

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
        """Concept-aware retrieval calling hybrid RRF retrieval."""
        q = (query or question).strip()
        cid = concept_id or concept
        return self.retrieve_hybrid(
            query=q,
            concept=cid,
            chapter=chapter,
            topic=topic,
            top_k=top_k,
        )

    def retrieve_hybrid(
        self,
        query: str,
        concept: str = "",
        chapter: str = "",
        topic: str = "",
        difficulty: str = "",
        content_type: str = "",
        top_k: int = 3,
    ) -> RAGContext:
        """Hybrid RAG combining Vector Search + BM25 Lexical + Metadata Filters via RRF."""
        q = query.strip()
        if not q:
            return RAGContext(query=q, results=[], confidence=ConfidenceLevel.LOW, status=RAGStatus.RAG_EMPTY)

        try:
            # 1. Vector Candidate Retrieval
            vector_candidates = self.store.search_similar(q, top_k=max(1, top_k * 3))
        except Exception as e:
            logger.error(f"RAG Store search error: {e}")
            return RAGContext(query=q, results=[], confidence=ConfidenceLevel.LOW, status=RAGStatus.RAG_ERROR, error_message=str(e))

        if not vector_candidates:
            return RAGContext(query=q, results=[], confidence=ConfidenceLevel.LOW, status=RAGStatus.RAG_EMPTY)

        # 2. Metadata Filtering & BM25 Scoring
        filtered_candidates: list[tuple[DocumentChunk, float, float]] = []
        for chunk, vec_score in vector_candidates:
            # Metadata filter checks
            if chapter and chunk.chapter and chapter.lower() not in chunk.chapter.lower():
                continue
            if topic and chunk.topic and topic.lower() not in chunk.topic.lower():
                continue
            if concept and getattr(chunk, "concept", "") and concept.lower() not in getattr(chunk, "concept", "").lower():
                continue
            if difficulty and getattr(chunk, "difficulty", "") and difficulty.lower() != getattr(chunk, "difficulty", "").lower():
                continue
            if content_type and getattr(chunk, "content_type", "") and content_type.lower() != getattr(chunk, "content_type", "").lower():
                continue

            bm25_score = BM25LexicalScorer.score_chunk(q, chunk.text)
            filtered_candidates.append((chunk, vec_score, bm25_score))

        # Fallback to unfiltered candidates if metadata filter was too restrictive
        if not filtered_candidates:
            filtered_candidates = [(c, vs, BM25LexicalScorer.score_chunk(q, c.text)) for c, vs in vector_candidates]

        # 3. Reciprocal Rank Fusion (RRF)
        # Sort candidates by Vector Rank and Lexical Rank
        vec_sorted = sorted(filtered_candidates, key=lambda x: x[1], reverse=True)
        lex_sorted = sorted(filtered_candidates, key=lambda x: x[2], reverse=True)

        vec_ranks = {c.chunk_id: rank + 1 for rank, (c, _, _) in enumerate(vec_sorted)}
        lex_ranks = {c.chunk_id: rank + 1 for rank, (c, _, _) in enumerate(lex_sorted)}

        results: list[RetrievalResult] = []
        for chunk, vec_score, _ in filtered_candidates:
            v_rank = vec_ranks[chunk.chunk_id]
            l_rank = lex_ranks[chunk.chunk_id]
            rrf_score = (1.0 / (RRF_K_CONSTANT + v_rank)) + (1.0 / (RRF_K_CONSTANT + l_rank))

            # Provenance weight booster
            prov_boost = SOURCE_PRIORITY_WEIGHTS.get(chunk.provenance_type, 1.0) / 10.0
            final_score = vec_score + (rrf_score * prov_boost)

            if vec_score >= HIGH_CONFIDENCE_THRESHOLD or rrf_score > 0.030:
                conf = ConfidenceLevel.HIGH
            elif vec_score >= MEDIUM_CONFIDENCE_THRESHOLD or rrf_score > 0.015:
                conf = ConfidenceLevel.MEDIUM
            else:
                conf = ConfidenceLevel.LOW

            results.append(RetrievalResult(chunk=chunk, score=round(vec_score, 4), rrf_score=round(rrf_score, 4), confidence=conf))

        results.sort(
            key=lambda r: (
                SOURCE_PRIORITY_WEIGHTS.get(getattr(r.chunk, "provenance_type", "NCERT"), 1.0),
                r.rrf_score + r.score,
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

        # 4. Generate Structured EvidenceCard
        evidence_card = None
        if final_results:
            top_chunk = final_results[0].chunk
            evidence_card = EvidenceCard(
                concept=top_chunk.concept or top_chunk.topic or "Chemistry Concept",
                definition=top_chunk.text[:200],
                intuition=f"Key authoritative evidence from {top_chunk.chapter}",
                formula="delta G = delta H - T delta S" if "entropy" in top_chunk.text.lower() or "gibbs" in top_chunk.text.lower() else "",
                misconceptions=[],
                examples=[f"See {top_chunk.chapter} Section {top_chunk.section}"],
                prerequisites=[],
                source=top_chunk.source_id,
                page=top_chunk.page,
                confidence=overall_confidence.value,
            )

        return RAGContext(
            query=q,
            results=final_results,
            confidence=overall_confidence,
            status=RAGStatus.RAG_OK,
            evidence_card=evidence_card,
        )

    def retrieve_atomic(self, concept_id: str, query: str = "") -> str:
        """Retrieve ultra-compact atomic card."""
        import json
        from core.config import BASE_DIR

        atomic_dir = BASE_DIR / "data" / "rag" / "atomic"
        if not atomic_dir.exists():
            return ""

        cid_norm = (concept_id or "").upper().strip()
        matched_card = None

        for json_file in atomic_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for card in data.get("cards", []):
                        card_cid = card.get("concept_id", "").upper().strip()
                        if cid_norm and card_cid == cid_norm:
                            matched_card = card
                            break
                        if not matched_card and query:
                            q_lower = query.lower()
                            cname_lower = card.get("concept_name", "").lower()
                            if card_cid.lower() in q_lower or (cname_lower and cname_lower in q_lower):
                                matched_card = card
                    if matched_card and cid_norm and matched_card.get("concept_id", "").upper().strip() == cid_norm:
                        break
            except Exception as exc:
                logger.debug(f"Failed to read atomic card {json_file}: {exc}")
                continue

        if not matched_card:
            return ""

        lines = [
            "<ncert_evidence>",
            f"[CONCEPT: {matched_card.get('concept_name', matched_card.get('concept_id'))}]",
            f"PRINCIPLE: {matched_card.get('principle', '')}",
            f"FORMULA/IUPAC: {matched_card.get('formula_iupac', '')}",
            f"ANALOGY: {matched_card.get('socratic_analogy', '')}",
            f"MISCONCEPTION: {matched_card.get('common_misconception', '')}",
            f"PREREQUISITE: {matched_card.get('prerequisite', '')}",
            "</ncert_evidence>"
        ]
        return "\n".join(lines)


_global_retriever: NCERTRetriever | None = None


def get_ncert_retriever() -> NCERTRetriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = NCERTRetriever()
    return _global_retriever
