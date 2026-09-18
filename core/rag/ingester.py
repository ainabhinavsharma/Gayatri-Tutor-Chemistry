"""Gayatri AI — Document Ingesting & Chunking Engine.

Processes NCERT textbook JSON data into schema-compliant DocumentChunk objects.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from core.rag.schema import DocumentChunk, SourceMetadata

logger = logging.getLogger("gayatri.rag.ingester")


class NCERTIngester:
    """Ingests NCERT document JSONs and generates deterministic chunks."""

    @staticmethod
    def generate_chunk_id(source_id: str, topic: str, subtopic: str, page: int, index: int) -> str:
        """Create a deterministic unique chunk ID using SHA256."""
        raw = f"{source_id}:{topic}:{subtopic}:{page}:{index}"
        return f"chk_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"

    def parse_file(self, json_path: str | Path) -> list[DocumentChunk]:
        """Parse a JSON file containing NCERT chapter sections into DocumentChunk instances."""
        path = Path(json_path)
        if not path.exists():
            logger.error(f"Ingestion file not found: {path}")
            return []

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        source_id = data.get("source_id", "NCERT_UNKNOWN")
        chapter = data.get("chapter", "Unknown Chapter")
        sections = data.get("sections", [])

        chunks: list[DocumentChunk] = []
        for idx, sec in enumerate(sections):
            topic = sec.get("topic", "General")
            subtopic = sec.get("subtopic", "General")
            page = sec.get("page", 0)
            text = sec.get("text", "").strip()

            if not text:
                continue

            chunk_id = self.generate_chunk_id(source_id, topic, subtopic, page, idx)
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                source_id=source_id,
                chapter=chapter,
                topic=topic,
                subtopic=subtopic,
                page=page,
                text=text,
                embedding_id=f"emb_{chunk_id}",
            )
            chunks.append(chunk)

        logger.info(f"Ingested {len(chunks)} chunks from {path.name} ({source_id})")
        return chunks
