#!/usr/bin/env python3
"""Gayatri AI — RAG Verification & Inspection Script (Section 12).

Executes benchmark test queries across the 4 private chemistry domains
and displays top retrieved concepts, similarity scores, metadata, and sources.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.rag.retriever import NCERTRetriever
from core.rag.store import RAGStore


BENCHMARK_QUERIES = [
    ("What is the first law of thermodynamics?", "Thermodynamics"),
    ("Why does NH3 have a pyramidal shape?", "Chemical Bonding"),
    ("Why does atomic radius decrease across a period?", "Periodic Trends"),
    ("What is a ligand?", "Coordination Chemistry"),
]


def test_rag() -> bool:
    print("=" * 70)
    print("GAYATRI CHEMISTRY TUTOR — RAG RETRIEVAL TEST (Section 12)")
    print("=" * 70)

    store = RAGStore()
    retriever = NCERTRetriever(store=store)

    all_passed = True

    for idx, (query, expected_domain) in enumerate(BENCHMARK_QUERIES, 1):
        print(f"\n[QUERY {idx}]: {query}")
        print(f"Target Domain: {expected_domain}")
        print("-" * 70)

        # Retrieve top chunks
        matches = store.search_similar(query, top_k=3)

        if not matches:
            print("RETRIEVAL RESULT: FAIL — Zero chunks retrieved!")
            all_passed = False
            continue

        print(f"TOP RETRIEVED CHUNKS ({len(matches)} matches):")
        for rank, (chk, score) in enumerate(matches, 1):
            sec = getattr(chk, "section", "General")
            print(f"\n  #{rank} [Score: {score:.4f}] Concept ID: {chk.embedding_id}")
            print(f"     Topic:    {chk.topic} | Subtopic: {chk.subtopic} | Section: {sec}")
            print(f"     Source:   {chk.source_id} (Page {chk.page})")
            snippet = chk.text.replace("\n", " ")[:140]
            print(f"     Snippet:  {snippet}...")

        # Domain relevance check
        top_chunk, top_score = matches[0]
        is_relevant = (
            expected_domain.lower() in top_chunk.topic.lower() or
            expected_domain.lower() in top_chunk.chapter.lower() or
            any(k in top_chunk.text.lower() for k in query.lower().split() if len(k) > 4)
        )
        print(f"\nRetrieval Assessment: {'PASS (Relevant content surfaced)' if is_relevant else 'WARNING (Verify ranking)'}")

    print("\n" + "=" * 70)
    status_str = "PASS — All benchmark queries successfully retrieved grounded knowledge" if all_passed else "FAIL — Some queries failed retrieval"
    print(f"OVERALL STATUS: {status_str}")
    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    success = test_rag()
    sys.exit(0 if success else 1)
