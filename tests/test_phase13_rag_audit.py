"""Phase 13: RAG Audit & Retrieval Verification Tests (Section 19).

Verifies:
1. Multi-factor retrieval considers: question, domain, chapter, topic, concept, learning objective.
2. Source priority: NCERT (10.0) -> Approved curriculum material (5.0) -> Controlled fallback (1.0).
3. Preservation of all 5 metadata fields: source, chapter, page/section, chunk ID, retrieval score.
4. Explicit tracking of RAG_OK, RAG_EMPTY, RAG_ERROR.
5. Controlled fallback enforcement: never silently turns RAG failure into unrestricted generation.
6. Ingestion resilience: handles UTF-8 BOM, missing files, and malformed JSON cleanly.
"""
import pytest
from core.rag.schema import (
    ConfidenceLevel,
    DocumentChunk,
    RAGContext,
    RAGStatus,
    RetrievalResult,
    SourceMetadata,
)
from core.rag.store import RAGStore
from core.rag.retriever import NCERTRetriever
from core.rag.ingester import NCERTIngester


def test_rag_status_enum_and_tracking():
    """Verify Section 19: explicitly track RAG_OK, RAG_EMPTY, RAG_ERROR."""
    assert RAGStatus.RAG_OK == "RAG_OK"
    assert RAGStatus.RAG_EMPTY == "RAG_EMPTY"
    assert RAGStatus.RAG_ERROR == "RAG_ERROR"

    # Verify helper properties on RAGContext
    ctx_ok = RAGContext(query="test", status=RAGStatus.RAG_OK)
    assert ctx_ok.is_ok is True
    assert ctx_ok.is_empty is False
    assert ctx_ok.is_error is False
    assert ctx_ok.is_fallback is False

    ctx_empty = RAGContext(query="test", status=RAGStatus.RAG_EMPTY)
    assert ctx_empty.is_ok is False
    assert ctx_empty.is_empty is True
    assert ctx_empty.is_error is False
    assert ctx_empty.is_fallback is True

    ctx_err = RAGContext(query="test", status=RAGStatus.RAG_ERROR, error_message="DB connection failed")
    assert ctx_err.is_ok is False
    assert ctx_err.is_empty is False
    assert ctx_err.is_error is True
    assert ctx_err.is_fallback is True


def test_preserve_all_five_metadata_fields():
    """Verify Section 19: preserve source, chapter, page/section, chunk ID, retrieval score."""
    chunk = DocumentChunk(
        chunk_id="chk_thermo_001",
        source_id="NCERT_CHEM_11_CH6",
        chapter="Thermodynamics",
        topic="Hess Law",
        subtopic="Standard Enthalpy",
        page=165,
        section="6.4",
        text="The standard enthalpy of reaction is the enthalpy change for a reaction under standard conditions.",
        provenance_type="NCERT",
    )

    result = RetrievalResult(
        chunk=chunk,
        score=0.925,
        confidence=ConfidenceLevel.HIGH,
    )

    # 1. source
    assert result.source == "NCERT_CHEM_11_CH6"
    assert chunk.source == "NCERT_CHEM_11_CH6"

    # 2. chapter
    assert result.chapter == "Thermodynamics"

    # 3. page / section
    assert result.page == 165
    assert result.section == "6.4"
    assert result.page_or_section == "p. 165, sec. 6.4"

    # 4. chunk ID
    assert result.chunk_id == "chk_thermo_001"
    assert chunk.id == "chk_thermo_001"

    # 5. retrieval score
    assert result.retrieval_score == 0.925
    assert result.score == 0.925

    # Verify serialization preserves all 5 fields
    d = result.to_dict()
    assert d["source"] == "NCERT_CHEM_11_CH6"
    assert d["chapter"] == "Thermodynamics"
    assert d["page"] == 165
    assert d["section"] == "6.4"
    assert d["chunk_id"] == "chk_thermo_001"
    assert d["retrieval_score"] == 0.925


def test_multi_factor_retrieval(tmp_path):
    """Verify Section 19: retrieval considers question, domain, chapter, topic, concept, and learning objective."""
    db_path = str(tmp_path / "multifactor_rag.db")
    store = RAGStore(db_path=db_path)
    retriever = NCERTRetriever(store=store)

    chunk = DocumentChunk(
        chunk_id="chk_entropy_spontaneity",
        source_id="NCERT_CH6",
        chapter="Thermodynamics",
        topic="Entropy",
        subtopic="Second Law",
        page=170,
        section="6.6",
        text="For an isolated system, the change in entropy is positive for a spontaneous process.",
        provenance_type="NCERT",
    )
    store.add_chunks([chunk])

    # Query incorporates question, domain, chapter, topic, concept, and learning_objective
    ctx = retriever.retrieve_concept_aware(
        question="What is the condition for spontaneity in isolated systems?",
        domain="Thermodynamics",
        chapter="Thermodynamics",
        topic="Entropy",
        concept="thermo.entropy",
        learning_objective="Understand delta S criterion for spontaneity",
        top_k=1,
    )

    assert ctx.status == RAGStatus.RAG_OK
    assert ctx.is_ok is True
    assert len(ctx.results) == 1
    assert ctx.results[0].chunk_id == "chk_entropy_spontaneity"
    assert ctx.results[0].chapter == "Thermodynamics"
    assert ctx.results[0].section == "6.6"
    assert ctx.results[0].retrieval_score > 0.1


def test_source_priority_ordering(tmp_path):
    """Verify Section 19 source priority: NCERT -> approved curriculum material -> controlled fallback."""
    db_path = str(tmp_path / "priority_rag.db")
    store = RAGStore(db_path=db_path)
    retriever = NCERTRetriever(store=store)

    # Add 3 chunks with identical topic and text but different provenance
    text_content = "Gibbs free energy change delta G = delta H - T delta S determines reaction spontaneity."

    chunk_ncert = DocumentChunk(
        chunk_id="chunk_ncert",
        source_id="NCERT_TXT",
        chapter="Thermodynamics",
        topic="Gibbs Free Energy",
        subtopic="Spontaneity",
        page=175,
        text=text_content,
        provenance_type="NCERT",
    )
    chunk_approved = DocumentChunk(
        chunk_id="chunk_approved",
        source_id="APPROVED_CURRICULUM_TXT",
        chapter="Thermodynamics",
        topic="Gibbs Free Energy",
        subtopic="Spontaneity",
        page=40,
        text=text_content,
        provenance_type="APPROVED_CURRICULUM",
    )
    chunk_fallback = DocumentChunk(
        chunk_id="chunk_fallback",
        source_id="FALLBACK_TXT",
        chapter="Thermodynamics",
        topic="Gibbs Free Energy",
        subtopic="Spontaneity",
        page=1,
        text=text_content,
        provenance_type="FALLBACK",
    )

    # Add in reverse priority order
    store.add_chunks([chunk_fallback, chunk_approved, chunk_ncert])

    ctx = retriever.retrieve_concept_aware(query="Gibbs free energy spontaneity", top_k=3)
    assert len(ctx.results) == 3

    # Ranking must strictly adhere to NCERT -> APPROVED_CURRICULUM -> FALLBACK
    assert ctx.results[0].chunk.provenance_type == "NCERT"
    assert ctx.results[1].chunk.provenance_type == "APPROVED_CURRICULUM"
    assert ctx.results[2].chunk.provenance_type == "FALLBACK"


def test_controlled_fallback_never_unrestricted_generation():
    """Verify Section 19: never silently turn RAG failure into unrestricted generation."""
    # 1. RAG_EMPTY scenario
    ctx_empty = RAGContext(
        query="unknown obscure chemistry reaction",
        results=[],
        confidence=ConfidenceLevel.LOW,
        status=RAGStatus.RAG_EMPTY,
    )
    assert ctx_empty.is_fallback is True
    evidence_empty = ctx_empty.formatted_evidence()
    assert "[CONTROLLED RAG FALLBACK: RAG_EMPTY]" in evidence_empty
    assert "Do NOT hallucinate unsupported details" in evidence_empty

    # 2. RAG_ERROR scenario
    ctx_error = RAGContext(
        query="calculate delta H",
        results=[],
        confidence=ConfidenceLevel.LOW,
        status=RAGStatus.RAG_ERROR,
        error_message="Connection timeout to vector store",
    )
    assert ctx_error.is_fallback is True
    evidence_error = ctx_error.formatted_evidence()
    assert "[CONTROLLED RAG FALLBACK: RAG_ERROR]" in evidence_error
    assert "Connection timeout" in evidence_error
    assert "Do NOT extrapolate or invent facts" in evidence_error


def test_ingester_resilience_and_bom_handling(tmp_path):
    """Verify NCERTIngester handles UTF-8 BOM, missing files, and malformed files safely without silent crashes."""
    ingester = NCERTIngester()

    # 1. Missing file returns empty list
    missing_res = ingester.parse_file(tmp_path / "non_existent.json")
    assert missing_res == []

    # 2. File with UTF-8 BOM is successfully parsed
    bom_file = tmp_path / "bom_sample.json"
    content = (
        '{\n'
        '  "source_id": "NCERT_CH6",\n'
        '  "chapter": "Thermodynamics",\n'
        '  "sections": [\n'
        '    {"topic": "Hess", "subtopic": "Law", "page": 160, "text": "Hess law summation."}\n'
        '  ]\n'
        '}'
    )
    # Write with utf-8-sig to inject UTF-8 BOM
    bom_file.write_bytes(content.encode("utf-8-sig"))

    bom_res = ingester.parse_file(bom_file)
    assert len(bom_res) == 1
    assert bom_res[0].topic == "Hess"

    # 3. Malformed JSON file returns empty list without raising unhandled exception
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{ unclosed json", encoding="utf-8")
    corrupt_res = ingester.parse_file(corrupt_file)
    assert corrupt_res == []
