"""Gayatri AI — RAG SQLite Document Store.

Stores chunks and provides lexical/TF-IDF similarity searching.
"""
from __future__ import annotations

import logging
import math
import re
import sqlite3
from pathlib import Path
from typing import Optional

from core.config import DB_PATH
from core.db import get_safe_db_connection
from core.rag.schema import DocumentChunk, SourceMetadata

logger = logging.getLogger("gayatri.rag.store")


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lower-case alphanumeric terms."""
    return set(re.findall(r"\w+", text.lower()))


class RAGStore:
    """SQLite-backed document chunk store with lexical and term overlap retrieval."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
        self._db_conn: Optional[sqlite3.Connection] = None
        self._create_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._db_conn is None:
            self._db_conn = get_safe_db_connection(self.db_path)
        return self._db_conn

    def _create_schema(self) -> None:
        from core.db import run_migrations
        conn = self.conn

        def migration_1(c: sqlite3.Connection) -> None:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS rag_sources (
                    source_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    class_level TEXT NOT NULL,
                    chapter TEXT NOT NULL,
                    subject TEXT DEFAULT 'Chemistry',
                    source_type TEXT DEFAULT 'textbook',
                    version TEXT DEFAULT 'NCERT 2023-24',
                    license TEXT DEFAULT 'NCERT Educational',
                    checksum TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    chapter TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    subtopic TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    section TEXT DEFAULT '',
                    text TEXT NOT NULL,
                    embedding_id TEXT DEFAULT '',
                    provenance_type TEXT DEFAULT 'NCERT',
                    FOREIGN KEY (source_id) REFERENCES rag_sources(source_id) ON DELETE CASCADE
                );
            """)

        def migration_2(c: sqlite3.Connection) -> None:
            try:
                c.execute("ALTER TABLE rag_chunks ADD COLUMN section TEXT DEFAULT '';")
            except sqlite3.OperationalError:
                pass

            try:
                c.execute("ALTER TABLE rag_chunks ADD COLUMN provenance_type TEXT DEFAULT 'NCERT';")
            except sqlite3.OperationalError:
                pass

        def migration_3(c: sqlite3.Connection) -> None:
            c.executescript("""
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks(source_id);
                CREATE INDEX IF NOT EXISTS idx_rag_chunks_chapter_topic ON rag_chunks(chapter, topic);
            """)

        migrations = {
            1: ("rag_initial_schema", migration_1),
            2: ("rag_section_provenance_columns", migration_2),
            3: ("rag_retrieval_indexes", migration_3),
        }

        run_migrations(conn, migrations)

    def add_source(self, source: SourceMetadata) -> None:
        """Insert or replace a source document metadata record."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO rag_sources (source_id, title, class_level, chapter, subject, source_type, version, license, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    title=excluded.title,
                    class_level=excluded.class_level,
                    chapter=excluded.chapter
            """, (
                source.source_id, source.title, source.class_level, source.chapter,
                source.subject, source.source_type, source.version, source.license, source.checksum
            ))

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Insert or replace chunks in the store, ensuring source records exist."""
        with self.conn:
            for chk in chunks:
                self.conn.execute("""
                    INSERT OR IGNORE INTO rag_sources (source_id, title, class_level, chapter)
                    VALUES (?, ?, 'Class 11', ?)
                """, (chk.source_id, f"Source {chk.source_id}", chk.chapter))

                sec = getattr(chk, "section", "")
                prov = getattr(chk, "provenance_type", "NCERT")
                self.conn.execute("""
                    INSERT INTO rag_chunks (chunk_id, source_id, chapter, topic, subtopic, page, section, text, embedding_id, provenance_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                        text=excluded.text,
                        topic=excluded.topic,
                        subtopic=excluded.subtopic,
                        page=excluded.page,
                        section=excluded.section,
                        provenance_type=excluded.provenance_type
                """, (
                    chk.chunk_id, chk.source_id, chk.chapter, chk.topic,
                    chk.subtopic, chk.page, sec, chk.text, chk.embedding_id,
                    prov
                ))
        logger.info(f"Stored {len(chunks)} chunks in RAG database")

    def get_all_chunks(self) -> list[DocumentChunk]:
        """Fetch all chunks from the database."""
        cursor = self.conn.execute("SELECT * FROM rag_chunks")
        chunks = []
        for row in cursor.fetchall():
            keys = row.keys() if hasattr(row, "keys") else []
            chunks.append(DocumentChunk(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                chapter=row["chapter"],
                topic=row["topic"],
                subtopic=row["subtopic"],
                page=row["page"],
                section=row["section"] if "section" in keys else "",
                text=row["text"],
                embedding_id=row["embedding_id"] if "embedding_id" in keys else "",
                provenance_type=row["provenance_type"] if "provenance_type" in keys else "NCERT",
            ))
        return chunks

    def search_similar(self, query: str, top_k: int = 3) -> list[tuple[DocumentChunk, float]]:
        """Perform term-overlap / Jaccard similarity search over chunks."""
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        chunks = self.get_all_chunks()
        results: list[tuple[DocumentChunk, float]] = []

        for chk in chunks:
            text_terms = _tokenize(f"{chk.topic} {chk.subtopic} {chk.text}")
            if not text_terms:
                continue

            intersection = query_terms.intersection(text_terms)
            if not intersection:
                continue

            # Calculate weighted score (boost exact topic matches)
            jaccard = len(intersection) / len(query_terms.union(text_terms))
            topic_overlap = len(query_terms.intersection(_tokenize(chk.topic)))
            boost = 1.5 if topic_overlap > 0 else 1.0

            score = min(1.0, (len(intersection) / len(query_terms)) * boost)
            if score > 0.05:
                results.append((chk, round(score, 4)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
