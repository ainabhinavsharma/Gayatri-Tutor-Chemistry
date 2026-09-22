#!/usr/bin/env python3
"""Gayatri AI — Private Chemistry Knowledge Base Ingestion Script (Section 11).

Discovers private Markdown files in PRIVATE_WORK/knowledge/, validates metadata,
splits content preserving conceptual boundaries, extracts prerequisites,
and indexes all chunks into the SQLite RAG store.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.rag.schema import DocumentChunk, SourceMetadata
from core.rag.store import RAGStore


def parse_markdown_concept(file_path: Path) -> dict:
    """Parse a concept Markdown file into structured sections and metadata."""
    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        return {"error": "Empty file"}

    # Extract sections by heading
    sections = {}
    current_heading = "HEADER"
    current_lines = []

    for line in content.splitlines():
        h2_match = re.match(r"^##\s+(.+)$", line)
        h1_match = re.match(r"^#\s+(.+)$", line)
        if h2_match:
            sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = h2_match.group(1).strip()
            current_lines = []
        elif h1_match and current_heading == "HEADER":
            sections["TITLE"] = h1_match.group(1).strip()
        else:
            current_lines.append(line)
    sections[current_heading] = "\n".join(current_lines).strip()

    concept_id = sections.get("Concept ID", "").strip()
    topic = sections.get("Topic", "").strip()
    subtopic = sections.get("Subtopic", "").strip() or file_path.stem.replace("_", " ").title()
    level = sections.get("Level", "Class 11 / Foundation").strip()

    # Parse prerequisites
    prereqs_raw = sections.get("Prerequisites", "")
    prerequisites = []
    for line in prereqs_raw.splitlines():
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            p_name = line.lstrip("-*").strip()
            if p_name:
                prerequisites.append(p_name)

    if not concept_id:
        return {"error": f"Missing Concept ID in {file_path.name}"}

    return {
        "concept_id": concept_id,
        "title": sections.get("TITLE", concept_id),
        "topic": topic or file_path.parent.name.replace("_", " ").title(),
        "subtopic": subtopic,
        "level": level,
        "prerequisites": prerequisites,
        "definition": sections.get("Definition", ""),
        "intuition": sections.get("Intuition", ""),
        "formula": sections.get("Formula", ""),
        "misconceptions": sections.get("Common Misconceptions", ""),
        "hints": sections.get("Teaching Hints", ""),
        "easy_q": sections.get("Easy Question", ""),
        "medium_q": sections.get("Medium Question", ""),
        "advanced_q": sections.get("Advanced Question", ""),
        "expected": sections.get("Expected Understanding", ""),
        "related": sections.get("Related Concepts", ""),
        "source": sections.get("Source", "NCERT Chemistry"),
        "raw_content": content,
        "file_path": file_path,
    }


def ingest_knowledge(db_path: Path | None = None) -> bool:
    print("=" * 60)
    print("GAYATRI CHEMISTRY TUTOR — KNOWLEDGE INGESTION (Section 11)")
    print("=" * 60)

    kb_dir = root / "PRIVATE_WORK" / "knowledge"
    if not kb_dir.exists():
        print(f"ERROR: Knowledge directory not found: {kb_dir}")
        return False

    md_files = list(kb_dir.rglob("*.md"))
    print(f"Files found:          {len(md_files)}")

    valid_files = 0
    invalid_files = 0
    concepts_dict = {}
    errors = []
    chunks: list[DocumentChunk] = []
    all_prereqs = []

    # 1. Parse and validate all files
    for f in md_files:
        parsed = parse_markdown_concept(f)
        if "error" in parsed:
            invalid_files += 1
            errors.append(f"{f.name}: {parsed['error']}")
            continue

        cid = parsed["concept_id"]
        if cid in concepts_dict:
            invalid_files += 1
            errors.append(f"Duplicate concept ID: '{cid}' in {f.name} and {concepts_dict[cid]['file_path'].name}")
            continue

        valid_files += 1
        concepts_dict[cid] = parsed
        all_prereqs.extend([(cid, p) for p in parsed["prerequisites"]])

        # 2. Intelligent chunk creation preserving concept boundaries
        # Chunk 1: Definition and Intuition
        def_text = f"Concept: {parsed['title']}\nID: {cid}\nTopic: {parsed['topic']}\n\nDefinition:\n{parsed['definition']}\n\nIntuition:\n{parsed['intuition']}"
        chunks.append(DocumentChunk(
            chunk_id=f"{cid.lower()}_def",
            source_id=f"private_{f.parent.name}",
            chapter=parsed["topic"],
            topic=parsed["topic"],
            subtopic=parsed["subtopic"],
            page=1,
            section="Definition and Intuition",
            text=def_text.strip(),
            embedding_id=cid,
            provenance_type="NCERT",
        ))

        # Chunk 2: Formula & Mathematical Relationships (if present)
        if parsed["formula"]:
            formula_text = f"Concept: {parsed['title']}\nTopic: {parsed['topic']}\n\nFormula & Relationships:\n{parsed['formula']}"
            chunks.append(DocumentChunk(
                chunk_id=f"{cid.lower()}_formula",
                source_id=f"private_{f.parent.name}",
                chapter=parsed["topic"],
                topic=parsed["topic"],
                subtopic=parsed["subtopic"],
                page=2,
                section="Formula and Rules",
                text=formula_text.strip(),
                embedding_id=cid,
                provenance_type="NCERT",
            ))

        # Chunk 3: Misconceptions and Pedagogical Hints
        if parsed["misconceptions"] or parsed["hints"]:
            misc_text = f"Concept: {parsed['title']}\n\nCommon Misconceptions:\n{parsed['misconceptions']}\n\nTeaching Hints:\n{parsed['hints']}"
            chunks.append(DocumentChunk(
                chunk_id=f"{cid.lower()}_pedagogy",
                source_id=f"private_{f.parent.name}",
                chapter=parsed["topic"],
                topic=parsed["topic"],
                subtopic=parsed["subtopic"],
                page=3,
                section="Misconceptions and Hints",
                text=misc_text.strip(),
                embedding_id=cid,
                provenance_type="NCERT",
            ))

        # Chunk 4: Formative Assessment Questions
        if parsed["easy_q"] or parsed["medium_q"]:
            q_text = f"Concept: {parsed['title']}\n\nEasy Question:\n{parsed['easy_q']}\n\nMedium Question:\n{parsed['medium_q']}\n\nAdvanced Question:\n{parsed['advanced_q']}"
            chunks.append(DocumentChunk(
                chunk_id=f"{cid.lower()}_questions",
                source_id=f"private_{f.parent.name}",
                chapter=parsed["topic"],
                topic=parsed["topic"],
                subtopic=parsed["subtopic"],
                page=4,
                section="Practice Questions",
                text=q_text.strip(),
                embedding_id=cid,
                provenance_type="NCERT",
            ))

    print(f"Valid files:          {valid_files}")
    print(f"Invalid files:        {invalid_files}")
    if errors:
        print("\nErrors detected:")
        for err in errors:
            print(f"  - {err}")

    # 3. Store chunks in SQLite RAG store
    store = RAGStore(db_path=db_path)
    # Register private sources
    for topic_folder in ["thermodynamics", "chemical_bonding", "periodic_trends", "coordination_chemistry"]:
        store.add_source(SourceMetadata(
            source_id=f"private_{topic_folder}",
            title=f"Private Knowledge Base — {topic_folder.replace('_', ' ').title()}",
            class_level="Class 11/12",
            chapter=topic_folder.replace("_", " ").title(),
            subject="Chemistry",
            source_type="private_markdown",
            version="MVP v1.0",
            license="Private Local",
        ))

    store.add_chunks(chunks)

    print(f"Chunks created:       {len(chunks)}")
    print(f"Embeddings/Indexed:   {len(chunks)}")
    print(f"Concepts:             {len(concepts_dict)}")
    print(f"Prerequisite links:   {len(all_prereqs)}")

    # 4. Final index status
    success = (invalid_files == 0 and len(chunks) > 0)
    print("\n" + "=" * 60)
    print(f"Index status:         {'PASS' if success else 'FAIL'}")
    print("=" * 60)
    return success


if __name__ == "__main__":
    success = ingest_knowledge()
    sys.exit(0 if success else 1)
