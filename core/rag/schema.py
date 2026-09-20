"""Gayatri AI — RAG Data Schemas (Phase 7).

Defines schemas for NCERT source metadata, document chunks, retrieval results,
source provenance, citations, and observable RAG status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RAGStatus(str, Enum):
    RAG_OK = "RAG_OK"
    RAG_EMPTY = "RAG_EMPTY"
    RAG_ERROR = "RAG_ERROR"
    # Legacy aliases
    RAG_STATUS_OK = "RAG_OK"
    RAG_STATUS_EMPTY = "RAG_EMPTY"
    RAG_STATUS_ERROR = "RAG_ERROR"


@dataclass
class SourceMetadata:
    """Metadata for an ingested source document."""
    source_id: str
    title: str
    class_level: str
    chapter: str
    subject: str = "Chemistry"
    source_type: str = "textbook"
    version: str = "NCERT 2023-24"
    license: str = "NCERT Educational"
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "class_level": self.class_level,
            "chapter": self.chapter,
            "subject": self.subject,
            "source_type": self.source_type,
            "version": self.version,
            "license": self.license,
            "checksum": self.checksum,
        }


@dataclass
class DocumentChunk:
    """A granular chunk of an NCERT document preserved with metadata and provenance (P7-T02 & Section 19)."""
    chunk_id: str
    source_id: str
    chapter: str
    topic: str
    subtopic: str
    page: int
    text: str
    embedding_id: str = ""
    provenance_type: str = "NCERT"  # "NCERT", "APPROVED_CURRICULUM", "TRUSTED_CURRICULUM", "FALLBACK"
    section: str = ""

    @property
    def id(self) -> str:
        return self.chunk_id

    @property
    def source(self) -> str:
        return self.source_id

    @property
    def page_or_section(self) -> str:
        if self.section and self.page:
            return f"p. {self.page}, sec. {self.section}"
        elif self.section:
            return f"sec. {self.section}"
        return f"p. {self.page}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "source": self.source_id,
            "chapter": self.chapter,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "page": self.page,
            "section": self.section,
            "page_or_section": self.page_or_section,
            "text": self.text,
            "embedding_id": self.embedding_id,
            "provenance_type": self.provenance_type,
        }


@dataclass
class RetrievalResult:
    """Result of a RAG query lookup with score and provenance (Section 19 preserved fields)."""
    chunk: DocumentChunk
    score: float
    confidence: ConfidenceLevel

    @property
    def source(self) -> str:
        return self.chunk.source_id

    @property
    def chapter(self) -> str:
        return self.chunk.chapter

    @property
    def page(self) -> int:
        return self.chunk.page

    @property
    def section(self) -> str:
        return getattr(self.chunk, "section", "")

    @property
    def page_or_section(self) -> str:
        return getattr(self.chunk, "page_or_section", f"p. {self.chunk.page}")

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id

    @property
    def retrieval_score(self) -> float:
        return self.score

    def citation(self) -> str:
        prov = self.chunk.provenance_type
        sec_info = f", Sec: {self.chunk.section}" if getattr(self.chunk, "section", "") else ""
        return f"[{prov} {self.chunk.chapter}{sec_info}, Topic: {self.chunk.topic} (p. {self.chunk.page})]"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "chapter": self.chapter,
            "page": self.page,
            "section": self.section,
            "page_or_section": self.page_or_section,
            "chunk_id": self.chunk_id,
            "retrieval_score": self.retrieval_score,
            "score": self.score,
            "confidence": self.confidence.value,
            "chunk": self.chunk.to_dict(),
        }


@dataclass
class RAGContext:
    """Structured context ready for LLM prompt injection with observable RAG status and controlled fallback (Section 19)."""
    query: str
    results: list[RetrievalResult] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    status: RAGStatus = RAGStatus.RAG_OK
    error_message: str = ""

    @property
    def is_ok(self) -> bool:
        return self.status in (RAGStatus.RAG_OK, RAGStatus.RAG_STATUS_OK)

    @property
    def is_empty(self) -> bool:
        return self.status in (RAGStatus.RAG_EMPTY, RAGStatus.RAG_STATUS_EMPTY)

    @property
    def is_error(self) -> bool:
        return self.status in (RAGStatus.RAG_ERROR, RAGStatus.RAG_STATUS_ERROR)

    @property
    def is_fallback(self) -> bool:
        return not self.is_ok

    def controlled_fallback_prompt(self) -> str:
        """Controlled fallback prompt constraint when RAG retrieval is empty or errored.
        Prevents unrestricted generation or hallucinations.
        """
        if self.is_ok:
            return ""
        if self.is_error:
            return (
                "[CONTROLLED RAG FALLBACK: RAG_ERROR]\n"
                f"Retrieval encountered an error: {self.error_message or 'Store unavailable'}.\n"
                "Do NOT extrapolate or invent facts. Restrict answers strictly to verified NCERT core definitions. "
                "If uncertain, guide the student to rephrase or consult textbook fundamentals."
            )
        else:  # RAG_EMPTY
            return (
                "[CONTROLLED RAG FALLBACK: RAG_EMPTY]\n"
                "No direct NCERT textbook chunks matched the query.\n"
                "Do NOT hallucinate unsupported details. Stick strictly to fundamental NCERT Chemistry principles. "
                "Guide the student to specify the chapter or topic if more detail is needed."
            )

    def formatted_evidence(self) -> str:
        if not self.is_ok or not self.results or self.confidence == ConfidenceLevel.LOW:
            return self.controlled_fallback_prompt()
        evidence_lines = ["--- AUTHORITATIVE NCERT EVIDENCE ---"]
        for idx, res in enumerate(self.results, 1):
            evidence_lines.append(
                f"[{idx}] {res.chunk.text}\n    Citation: {res.citation()} (Score: {res.retrieval_score:.4f})"
            )
        evidence_lines.append("--- END NCERT EVIDENCE ---")
        return "\n".join(evidence_lines)
