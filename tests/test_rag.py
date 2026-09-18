"""Tests for Phase 5 — NCERT RAG Foundation."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from core.rag.schema import ConfidenceLevel, DocumentChunk, SourceMetadata
from core.rag.ingester import NCERTIngester
from core.rag.store import RAGStore
from core.rag.retriever import NCERTRetriever
from core.rag.citations import CitationFormatter


@pytest.fixture
def sample_sources_json(tmp_path) -> Path:
    p = tmp_path / "sources.json"
    p.write_text(json.dumps({
        "sources": [{
            "source_id": "TEST_SOURCE_1",
            "title": "Test Title",
            "class_level": "Class 11",
            "chapter": "Test Chapter"
        }]
    }), encoding="utf-8")
    return p


@pytest.fixture
def sample_chapter_json(tmp_path) -> Path:
    p = tmp_path / "ncert_test.json"
    p.write_text(json.dumps({
        "source_id": "NCERT_TEST_01",
        "chapter": "Thermodynamics",
        "sections": [
            {
                "topic": "First Law",
                "subtopic": "Energy Conservation",
                "page": 100,
                "text": "The First Law of Thermodynamics states that energy cannot be created or destroyed. delta U = q + w."
            },
            {
                "topic": "Hess's Law",
                "subtopic": "Enthalpy Summation",
                "page": 105,
                "text": "Hess's Law states that total enthalpy change of a reaction is independent of the pathway."
            }
        ]
    }), encoding="utf-8")
    return p


class TestRAGIngester:
    def test_chunk_ingestion(self, sample_chapter_json):
        ingester = NCERTIngester()
        chunks = ingester.parse_file(sample_chapter_json)
        assert len(chunks) == 2
        assert chunks[0].source_id == "NCERT_TEST_01"
        assert chunks[0].chapter == "Thermodynamics"
        assert chunks[0].topic == "First Law"
        assert "delta U = q + w" in chunks[0].text

    def test_nonexistent_file_returns_empty(self, tmp_path):
        ingester = NCERTIngester()
        chunks = ingester.parse_file(tmp_path / "missing.json")
        assert chunks == []


class TestRAGStoreAndRetriever:
    def test_store_and_retrieve(self, sample_chapter_json, tmp_path):
        ingester = NCERTIngester()
        chunks = ingester.parse_file(sample_chapter_json)

        store = RAGStore(db_path=tmp_path / "test_rag.db")
        store.add_chunks(chunks)

        retriever = NCERTRetriever(store=store)
        ctx = retriever.retrieve("What is the First Law of Thermodynamics?")

        assert ctx.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        assert len(ctx.results) > 0
        assert "First Law" in ctx.results[0].chunk.topic
        assert ctx.results[0].score > 0.2

    def test_low_confidence_on_irrelevant_query(self, sample_chapter_json, tmp_path):
        ingester = NCERTIngester()
        chunks = ingester.parse_file(sample_chapter_json)

        store = RAGStore(db_path=tmp_path / "test_rag.db")
        store.add_chunks(chunks)

        retriever = NCERTRetriever(store=store)
        ctx = retriever.retrieve("unrelated quantum computing algorithms xyz")

        assert ctx.confidence == ConfidenceLevel.LOW

    def test_empty_query_returns_low_confidence(self, tmp_path):
        store = RAGStore(db_path=tmp_path / "test_rag.db")
        retriever = NCERTRetriever(store=store)
        ctx = retriever.retrieve("")
        assert ctx.confidence == ConfidenceLevel.LOW
        assert ctx.results == []


class TestCitations:
    def test_citation_formatting(self):
        chunk = DocumentChunk(
            chunk_id="c1",
            source_id="S1",
            chapter="Thermodynamics",
            topic="First Law",
            subtopic="Formula",
            page=163,
            text="delta U = q + w",
        )
        cit = CitationFormatter.format_chunk_citation(chunk)
        assert "NCERT Chemistry (Thermodynamics)" in cit
        assert "p. 163" in cit
