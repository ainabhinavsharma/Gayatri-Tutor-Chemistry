"""Gayatri AI — Curriculum Adapters for National Standards (NCERT, CBSE).

Provides adapters to load, validate, and inject structured standardized
curricula with multilingual topic names and prerequisite trees into the
Learning Dependency Graph.
"""

from __future__ import annotations

import json
import logging
from abc import ABC
from pathlib import Path
from typing import Any

from core.knowledge_graph import LearningDependencyGraph

logger = logging.getLogger("gayatri.curriculum.adapters")


class BaseCurriculumAdapter(ABC):
    """Abstract base adapter for curriculum standards."""

    def __init__(self, curriculum_file: Path | str):
        self.file_path = Path(curriculum_file)
        self._data: dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Curriculum specification file not found: {self.file_path}")
        with open(self.file_path, encoding="utf-8-sig") as f:
            self._data = json.load(f)

    @property
    def board(self) -> str:
        return self._data.get("board", "Standard")

    @property
    def subject(self) -> str:
        return self._data.get("subject", "General")

    @property
    def grade(self) -> str:
        return self._data.get("grade", "Grade 9")

    @property
    def version(self) -> str:
        return self._data.get("version", "1.0")

    def get_concepts(self, lang: str = "en") -> list[dict[str, Any]]:
        """Return raw concept definitions with localized names."""
        concepts = []
        for c in self._data.get("concepts", []):
            name = c.get(f"name_{lang}") if lang != "en" and f"name_{lang}" in c else c["name"]
            concepts.append({**c, "localized_name": name})
        return concepts

    def load_into_graph(self, graph: LearningDependencyGraph, lang: str = "en") -> int:
        """Populate a LearningDependencyGraph with concepts and prerequisite edges."""
        concepts = self.get_concepts(lang=lang)
        count = 0

        # Pass 1: add all nodes
        for c in concepts:
            graph.add_concept(
                concept_id=c["id"],
                name=c["localized_name"],
                description=c.get("description", ""),
                difficulty=c.get("difficulty", 0.5),
                subject=self.subject.lower(),
                minimum_mastery=c.get("minimum_mastery", 0.85),
            )
            count += 1

        # Pass 2: add prerequisite edges
        for c in concepts:
            cid = c["id"]
            for prereq in c.get("prerequisites", []):
                graph.add_prerequisite(cid, prereq)

        logger.info(f"Loaded {count} {self.board} {self.subject} ({self.grade}) concepts into LDG.")
        return count


class CBSECurriculumAdapter(BaseCurriculumAdapter):
    """Adapter for Central Board of Secondary Education (CBSE) curricula."""

    @classmethod
    def for_subject_and_grade(cls, subject: str, grade: str) -> CBSECurriculumAdapter:
        base = Path(__file__).resolve().parent.parent.parent / "data" / "curriculum"
        clean_sub = subject.lower().strip()
        clean_grade = grade.lower().replace(" ", "").strip()
        path = base / clean_sub / f"{clean_grade}_cbse.json"
        return cls(path)


class NCERTCurriculumAdapter(BaseCurriculumAdapter):
    """Adapter for National Council of Educational Research and Training (NCERT) curricula."""

    @classmethod
    def for_subject_and_grade(cls, subject: str, grade: str) -> NCERTCurriculumAdapter:
        base = Path(__file__).resolve().parent.parent.parent / "data" / "curriculum"
        clean_sub = subject.lower().strip()
        clean_grade = grade.lower().replace(" ", "").strip()
        path = base / clean_sub / f"{clean_grade}_ncert.json"
        return cls(path)
