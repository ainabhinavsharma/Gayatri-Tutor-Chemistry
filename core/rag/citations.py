"""Gayatri AI — Citation Formatter.

Formats authoritative NCERT source citations based exclusively on ingested chunk metadata.
Prevents fabricated page numbers or invalid source claims.
"""
from __future__ import annotations

from core.rag.schema import DocumentChunk, RetrievalResult


class CitationFormatter:
    """Formats explicit NCERT citations."""

    @staticmethod
    def format_chunk_citation(chunk: DocumentChunk) -> str:
        """Format citation for a single chunk."""
        return (
            f"Source: NCERT Chemistry ({chunk.chapter})\n"
            f"Topic: {chunk.topic} — {chunk.subtopic}\n"
            f"Reference Page: p. {chunk.page}"
        )

    @staticmethod
    def format_results_citations(results: list[RetrievalResult]) -> str:
        """Format a list of retrieval results into a clean markdown reference list."""
        if not results:
            return ""

        lines = ["**References & Citations:**"]
        seen = set()

        for res in results:
            c = res.chunk
            key = (c.source_id, c.chapter, c.topic, c.page)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- *NCERT Chemistry*, {c.chapter} ({c.topic}, p. {c.page})")

        return "\n".join(lines)
