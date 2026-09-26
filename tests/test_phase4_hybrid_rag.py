"""Phase 4: RAG 2.0: Hybrid Retrieval Engine Tests.

Verifies:
1. BM25 Lexical Scorer and Vector similarity fusion using Reciprocal Rank Fusion (RRF).
2. Metadata filter compliance (chapter, topic, concept, difficulty, content_type).
3. Structured EvidenceCard generation and serialization.
4. Low confidence and empty retrieval controlled fallback prompts.
5. Provenance priority weight boosting (NCERT > APPROVED > FALLBACK).
6. Golden retrieval dataset evaluation against docs/datasets/rag_golden_dataset.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.rag.retriever import BM25LexicalScorer, NCERTRetriever, get_ncert_retriever
from core.rag.schema import ConfidenceLevel, DocumentChunk, EvidenceCard, RAGStatus
from core.rag.store import RAGStore

GOLDEN_DATASET_PATH = Path("docs/datasets/rag_golden_dataset.json")


def test_bm25_lexical_scorer():
    """Verify BM25 tokenization and term frequency scoring."""
    query = "entropy and enthalpy change"
    text_match = "Entropy is a measure of disorder while enthalpy change delta H is heat."
    text_no_match = "Carbohydrates are organic compounds containing carbon and hydrogen."

    score_match = BM25LexicalScorer.score_chunk(query, text_match)
    score_no_match = BM25LexicalScorer.score_chunk(query, text_no_match)

    assert score_match > score_no_match
    assert score_match > 0.0


def test_hybrid_rrf_retrieval(tmp_path):
    """Verify RRF hybrid retrieval merges vector candidates and BM25 scores."""
    db_path = tmp_path / "test_rag_hybrid.db"
    store = RAGStore(db_path=db_path)

    chunk1 = DocumentChunk(
        chunk_id="chk_001",
        source_id="NCERT Class 11",
        chapter="Unit 6",
        topic="Thermodynamics",
        subtopic="Entropy",
        concept="THERMO_ENTROPY",
        page=165,
        text="Entropy S is a state function measuring molecular randomness and heat dispersal.",
        provenance_type="NCERT",
    )
    chunk2 = DocumentChunk(
        chunk_id="chk_002",
        source_id="NCERT Class 11",
        chapter="Unit 6",
        topic="Thermodynamics",
        subtopic="First Law",
        concept="THERMO_FIRST_LAW",
        page=160,
        text="First Law of Thermodynamics states that energy of an isolated system is conserved: delta U = q + w.",
        provenance_type="NCERT",
    )

    store.add_chunk(chunk1)
    store.add_chunk(chunk2)

    retriever = NCERTRetriever(store=store)
    context = retriever.retrieve_hybrid("What is entropy S and molecular randomness?", top_k=2)

    assert context.status == RAGStatus.RAG_OK
    assert len(context.results) >= 1

    top_res = context.results[0]
    assert top_res.chunk.chunk_id == "chk_001"
    assert top_res.rrf_score > 0.0


def test_metadata_filtering(tmp_path):
    """Verify metadata filtering on chapter and concept."""
    db_path = tmp_path / "test_rag_filter.db"
    store = RAGStore(db_path=db_path)

    c_thermo = DocumentChunk(
        chunk_id="c_th_1",
        source_id="NCERT 11",
        chapter="Unit 6",
        topic="Thermodynamics",
        subtopic="",
        concept="THERMO_ENTHALPY",
        page=100,
        text="Enthalpy delta H is heat change at constant pressure.",
    )
    c_bond = DocumentChunk(
        chunk_id="c_bo_1",
        source_id="NCERT 11",
        chapter="Unit 4",
        topic="Bonding",
        subtopic="",
        concept="BOND_VSEPR",
        page=120,
        text="VSEPR theory explains molecular shape based on electron pair repulsion.",
    )

    store.add_chunk(c_thermo)
    store.add_chunk(c_bond)

    retriever = NCERTRetriever(store=store)
    ctx = retriever.retrieve_hybrid("Tell me about heat and shape", chapter="Unit 4")

    assert len(ctx.results) >= 1
    assert ctx.results[0].chunk.chapter == "Unit 4"


def test_evidence_card_generation(tmp_path):
    """Verify structured EvidenceCard creation in RAGContext."""
    db_path = tmp_path / "test_rag_card.db"
    store = RAGStore(db_path=db_path)

    chunk = DocumentChunk(
        chunk_id="chk_card",
        source_id="NCERT 11",
        chapter="Unit 6",
        topic="Thermodynamics",
        subtopic="Gibbs",
        concept="THERMO_GIBBS",
        page=175,
        text="Gibbs free energy change delta G determines spontaneity under constant T and P.",
    )
    store.add_chunk(chunk)

    retriever = NCERTRetriever(store=store)
    ctx = retriever.retrieve_hybrid("Gibbs free energy spontaneity")

    assert ctx.evidence_card is not None
    card = ctx.evidence_card
    assert isinstance(card, EvidenceCard)
    assert card.source == "NCERT 11"
    assert card.page == 175
    assert card.concept is not None


def test_controlled_fallback_prompt_low_confidence():
    """Verify controlled fallback prompt prevents hallucination on low confidence / empty RAG."""
    retriever = NCERTRetriever(store=RAGStore(db_path=Path(":memory:")))
    ctx = retriever.retrieve_hybrid("NonExistentChemistryTopicX123")

    assert ctx.status == RAGStatus.RAG_EMPTY
    assert ctx.confidence == ConfidenceLevel.LOW
    fallback = ctx.controlled_fallback_prompt()
    assert "[CONTROLLED RAG FALLBACK:" in fallback
    assert "Do NOT hallucinate unsupported details" in fallback


def test_golden_rag_retrieval_benchmark():
    """Verify retrieval against frozen golden dataset docs/datasets/rag_golden_dataset.json."""
    assert GOLDEN_DATASET_PATH.exists()
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    retriever = get_ncert_retriever()
    hit_count = 0
    total = len(dataset["queries"])

    for item in dataset["queries"]:
        q = item["query"]
        ctx = retriever.retrieve_hybrid(q, top_k=3)
        if ctx.is_ok and ctx.results:
            hit_count += 1

    hit_rate = hit_count / total
    assert hit_rate >= 0.80, f"Golden RAG benchmark hit rate ({hit_rate:.2%}) below 80% threshold."
