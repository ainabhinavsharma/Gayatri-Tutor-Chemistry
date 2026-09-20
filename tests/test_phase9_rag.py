"""Tests for Phase 9: RAG Engine Re-Audit (P7-T01 to P7-T04)."""
import pytest
from core.rag.schema import DocumentChunk, SourceMetadata, ConfidenceLevel, RAGStatus
from core.rag.store import RAGStore
from core.rag.retriever import NCERTRetriever
from core.rag.citations import CitationFormatter


def test_rag_store_add_and_search(tmp_path):
    """Test chunk storage and lexical similarity search in RAGStore."""
    db_path = str(tmp_path / "test_rag.db")
    store = RAGStore(db_path=db_path)

    chunk1 = DocumentChunk(
        chunk_id="chunk_01",
        source_id="src_thermo",
        chapter="Thermodynamics",
        topic="Hess Law",
        subtopic="Enthalpy Calculation",
        page=160,
        text="The total enthalpy change in a reaction is constant regardless of the path taken.",
    )
    chunk2 = DocumentChunk(
        chunk_id="chunk_02",
        source_id="src_inorganic",
        chapter="Periodic Table",
        topic="Ionization Enthalpy",
        subtopic="Periodic Trends",
        page=85,
        text="Ionization enthalpy increases across a period due to increasing effective nuclear charge.",
    )

    store.add_chunks([chunk1, chunk2])

    # Search query matching chunk 1
    matches = store.search_similar("total enthalpy change reaction path", top_k=2)
    assert len(matches) >= 1
    best_chunk, score = matches[0]
    assert best_chunk.chunk_id == "chunk_01"
    assert score > 0.2


def test_retriever_empty_query(tmp_path):
    """Test that empty or whitespace query returns RAG_STATUS_EMPTY."""
    db_path = str(tmp_path / "test_rag.db")
    store = RAGStore(db_path=db_path)
    retriever = NCERTRetriever(store=store)

    res_empty = retriever.retrieve_concept_aware(query="")
    assert res_empty.status == RAGStatus.RAG_STATUS_EMPTY
    assert res_empty.confidence == ConfidenceLevel.LOW
    assert len(res_empty.results) == 0

    res_spaces = retriever.retrieve_concept_aware(query="   ")
    assert res_spaces.status == RAGStatus.RAG_STATUS_EMPTY


def test_retriever_concept_aware(tmp_path):
    """Test concept-aware retrieval with context query enrichment."""
    db_path = str(tmp_path / "test_rag.db")
    store = RAGStore(db_path=db_path)
    retriever = NCERTRetriever(store=store)

    chunk = DocumentChunk(
        chunk_id="chunk_gibbs",
        source_id="src_thermo",
        chapter="Thermodynamics",
        topic="Gibbs Free Energy",
        subtopic="Spontaneity Criteria",
        page=172,
        text="A reaction is spontaneous at constant temperature and pressure if delta G is less than zero.",
    )
    store.add_chunks([chunk])

    res = retriever.retrieve_concept_aware(
        query="spontaneous criteria",
        domain="Thermodynamics",
        chapter="Thermodynamics",
        topic="Gibbs Free Energy",
        concept_id="thermo.gibbs",
        top_k=1,
    )

    assert res.status == RAGStatus.RAG_STATUS_OK
    assert len(res.results) == 1
    assert res.results[0].chunk.chunk_id == "chunk_gibbs"


def test_retriever_provenance_priority(tmp_path):
    """Test provenance sorting prioritizing NCERT > TRUSTED_CURRICULUM > FALLBACK."""
    db_path = str(tmp_path / "test_rag.db")
    store = RAGStore(db_path=db_path)
    retriever = NCERTRetriever(store=store)

    chunk_ncert = DocumentChunk(
        chunk_id="ncert_1",
        source_id="src_1",
        chapter="Thermodynamics",
        topic="First Law",
        subtopic="Internal Energy",
        page=150,
        text="Delta U = q + w according to the first law of thermodynamics.",
        provenance_type="NCERT",
    )
    chunk_fallback = DocumentChunk(
        chunk_id="fallback_1",
        source_id="src_2",
        chapter="Thermodynamics",
        topic="First Law",
        subtopic="Internal Energy",
        page=10,
        text="Delta U = q + w according to the first law of thermodynamics.",
        provenance_type="FALLBACK",
    )
    store.add_chunks([chunk_fallback, chunk_ncert])

    res = retriever.retrieve_concept_aware("first law internal energy", top_k=2)
    assert len(res.results) == 2
    # NCERT chunk must be ranked first due to provenance weight
    assert res.results[0].chunk.provenance_type == "NCERT"


def test_citation_formatter():
    """Test citation formatting for chunks and retrieval results."""
    chunk = DocumentChunk(
        chunk_id="c1",
        source_id="ncert_chem_11",
        chapter="Thermodynamics",
        topic="Hess Law",
        subtopic="Standard Enthalpies",
        page=162,
        text="Enthalpy change is a state function.",
    )

    single_citation = CitationFormatter.format_chunk_citation(chunk)
    assert "Source: NCERT Chemistry (Thermodynamics)" in single_citation
    assert "Topic: Hess Law — Standard Enthalpies" in single_citation
    assert "Reference Page: p. 162" in single_citation

    from core.rag.schema import RetrievalResult
    results = [RetrievalResult(chunk=chunk, score=0.8, confidence=ConfidenceLevel.HIGH)]
    formatted_refs = CitationFormatter.format_results_citations(results)

    assert "**References & Citations:**" in formatted_refs
    assert "- *NCERT Chemistry*, Thermodynamics (Hess Law, p. 162)" in formatted_refs
