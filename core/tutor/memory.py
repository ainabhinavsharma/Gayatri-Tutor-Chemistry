"""Gayatri AI — Tutor Memory Manager.

Constructs concise pedagogical memory summaries for prompt injection.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("gayatri.tutor.memory")


@dataclass
class TutorMemorySummary:
    """Concise active memory for a tutoring session."""
    current_topic: str = ""
    current_subtopic: str = ""
    mastery_estimate: float = 0.5
    known_misconceptions: list[str] = field(default_factory=list)
    recent_errors: list[str] = field(default_factory=list)
    active_difficulty: int = 2

    def formatted_summary(self) -> str:
        """Format concise memory block for prompt injection."""
        lines = ["[PEDAGOGICAL STATE & MEMORY]"]
        if self.current_topic:
            lines.append(f"Current Topic: {self.current_topic}")
        if self.current_subtopic:
            lines.append(f"Current Subtopic: {self.current_subtopic}")
        lines.append(f"Mastery Estimate: {self.mastery_estimate * 100:.0f}%")
        lines.append(f"Target Difficulty Level: L{self.active_difficulty}")
        if self.known_misconceptions:
            lines.append(f"Known Misconceptions: {', '.join(self.known_misconceptions[:3])}")
        if self.recent_errors:
            lines.append(f"Recent Mistakes: {', '.join(self.recent_errors[:2])}")
        lines.append("[END PEDAGOGICAL MEMORY]")
        return "\n".join(lines)


class TutorMemoryManager:
    """Manages concise tutor state memory per session."""

    @staticmethod
    def build_memory(
        topic: str = "",
        subtopic: str = "",
        mastery: float = 0.5,
        misconceptions: Optional[list[str]] = None,
        difficulty: int = 2,
    ) -> TutorMemorySummary:
        return TutorMemorySummary(
            current_topic=topic,
            current_subtopic=subtopic,
            mastery_estimate=mastery,
            known_misconceptions=misconceptions or [],
            active_difficulty=difficulty,
        )
