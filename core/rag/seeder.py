"""Gayatri AI — Automated RAG Textbook Knowledge Seeder.

Ensures that NCERT textbook data (Thermodynamics, Inorganic, Physical Chemistry)
is automatically and idempotently ingested into SQLite on startup if rag_chunks is empty.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from core.config import BASE_DIR
from core.rag.ingester import NCERTIngester
from core.rag.schema import SourceMetadata
from core.rag.store import RAGStore

logger = logging.getLogger("gayatri.rag.seeder")


def seed_ncert_rag(
    store: Optional[RAGStore] = None,
    rag_dir: Optional[Path] = None,
) -> int:
    """Idempotently seed NCERT textbook chapters and sources into RAGStore.

    Returns:
        Number of chunks newly ingested (0 if already seeded).
    """
    rag_store = store or RAGStore()
    source_dir = rag_dir or (BASE_DIR / "data" / "rag")

    if not source_dir.exists():
        logger.warning(f"RAG data directory not found at: {source_dir}")
        return 0

    # 1. Check if store is already populated
    try:
        cursor = rag_store.conn.cursor()
        existing_count = cursor.execute(
            "SELECT count(*) FROM rag_chunks WHERE provenance_type = 'NCERT'"
        ).fetchone()[0]
        if existing_count > 0:
            logger.debug(f"RAGStore already seeded with {existing_count} NCERT chunks.")
            return 0
    except Exception as exc:
        logger.warning(f"Could not check existing RAG chunks: {exc}")

    # 2. Ingest sources metadata if sources.json exists
    sources_file = source_dir / "sources.json"
    if sources_file.is_file():
        try:
            with open(sources_file, "r", encoding="utf-8") as sf:
                sources_data = json.load(sf)
                for s in sources_data.get("sources", []):
                    meta = SourceMetadata(
                        source_id=s.get("source_id", "NCERT_DEFAULT"),
                        title=s.get("title", "NCERT Chemistry"),
                        class_level=s.get("class_level", "Class 11"),
                        chapter=s.get("chapter", "Chemistry"),
                        subject=s.get("subject", "Chemistry"),
                        version=s.get("version", "NCERT 2023-24"),
                    )
                    rag_store.add_source(meta)
        except Exception as exc:
            logger.warning(f"Failed to seed sources metadata from {sources_file}: {exc}")

    # 3. Ingest textbook section JSONs
    ingester = NCERTIngester()
    total_added = 0

    for json_file in sorted(source_dir.glob("*.json")):
        if json_file.name == "sources.json":
            continue
        try:
            chunks = ingester.parse_file(json_file)
            if chunks:
                rag_store.add_chunks(chunks)
                total_added += len(chunks)
                logger.info(f"Seeded {len(chunks)} chunks from {json_file.name}")
        except Exception as exc:
            logger.error(f"Failed to seed RAG chunks from {json_file}: {exc}")

    logger.info(f"RAG seeding complete. Total chunks ingested: {total_added}")
    return total_added
