"""Gayatri AI — RAG Data Schemas.

Defines schemas for NCERT source metadata, document chunks, retrieval results,
and citations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


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
    """A granular chunk of an NCERT document preserved with metadata."""
    chunk_id: str
    source_id: str
    chapter: str
    topic: str
    subtopic: str
    page: int
    text: str
    embedding_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "chapter": self.chapter,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "page": self.page,
            "text": self.text,
            "embedding_id": self.embedding_id,
        }


@dataclass
class RetrievalResult:
    """Result of a RAG query lookup."""
    chunk: DocumentChunk
    score: float
    confidence: ConfidenceLevel

    def citation(self) -> str:
        return f"[NCERT {self.chunk.chapter}, Topic: {self.chunk.topic} (p. {self.chunk.page})]"


@dataclass
class RAGContext:
    """Structured context ready for LLM prompt injection."""
    query: str
    results: list[RetrievalResult] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW

    def formatted_evidence(self) -> str:
        if not self.results or self.confidence == ConfidenceLevel.LOW:
            return ""
        evidence_lines = ["--- AUTHORITATIVE NCERT EVIDENCE ---"]
        for idx, res in enumerate(self.results, 1):
            evidence_lines.append(
                f"[{idx}] {res.chunk.text}\n    Citation: {res.citation()}"
            )
        evidence_lines.append("--- END NCERT EVIDENCE ---")
        return "\n".join(evidence_lines)
