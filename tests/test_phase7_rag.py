"""Phase 7 Test Suite: NCERT RAG and Evidence Control.

Verifies concept-aware retrieval, source priority ranking, and observable RAG status (P7-T01 through P7-T04).
"""
import pytest
from core.rag.retriever import NCERTRetriever
from core.rag.schema import DocumentChunk, RAGStatus
from core.rag.store import RAGStore


class MockStore(RAGStore):
    def __init__(self, fail: bool = False, empty: bool = False):
        self.fail = fail
        self.empty = empty

    def search_similar(self, query: str, top_k: int = 3):
        if self.fail:
            raise RuntimeError("Database connection failed")
        if self.empty:
            return []

        c1 = DocumentChunk(
            chunk_id="ch1",
            source_id="ncert.thermo",
            chapter="Thermodynamics",
            topic="Hess Law",
            subtopic="Enthalpy",
            page=12,
            text="Hess's law states that total enthalpy change is independent of pathway.",
            provenance_type="NCERT",
        )
        c2 = DocumentChunk(
            chunk_id="ch2",
            source_id="generic.web",
            chapter="Thermodynamics",
            topic="Hess Law",
            subtopic="General",
            page=1,
            text="Hess law web snippet.",
            provenance_type="FALLBACK",
        )
        return [(c1, 0.85), (c2, 0.90)]


def test_concept_aware_retrieval_and_priority():
    mock_store = MockStore()
    retriever = NCERTRetriever(store=mock_store)

    ctx = retriever.retrieve_concept_aware(
        query="What is Hess Law?",
        domain="Thermodynamics",
        chapter="Enthalpy Changes",
        topic="Hess Law",
        concept_id="thermo.hess_law",
    )

    assert ctx.status == RAGStatus.RAG_STATUS_OK
    assert len(ctx.results) >= 1
    # Check that NCERT provenance chunk is prioritized over FALLBACK
    top_chunk = ctx.results[0].chunk
    assert top_chunk.provenance_type == "NCERT"
    assert "AUTHORITATIVE NCERT EVIDENCE" in ctx.formatted_evidence()


def test_rag_empty_and_error_status():
    # Empty status
    retriever_empty = NCERTRetriever(store=MockStore(empty=True))
    ctx_empty = retriever_empty.retrieve_concept_aware("Unknown query")
    assert ctx_empty.status == RAGStatus.RAG_STATUS_EMPTY
    assert ctx_empty.formatted_evidence() == ""

    # Error status
    retriever_error = NCERTRetriever(store=MockStore(fail=True))
    ctx_err = retriever_error.retrieve_concept_aware("Query during failure")
    assert ctx_err.status == RAGStatus.RAG_STATUS_ERROR
    assert "failed" in ctx_err.error_message
