"""Gayatri AI — Student Adapter.

Adapts tutoring response parameters based on student profile and mastery metrics.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.profile import UserProfile

logger = logging.getLogger("gayatri.tutor.adapter")


@dataclass
class AdaptationStrategy:
    """Parameters controlling LLM prompt style and scaffolding."""
    response_depth: str  # "high_level", "standard", "deep_dive"
    terminology_level: str  # "simplified", "ncert_standard", "advanced"
    num_examples: int  # 1, 2, 3
    scaffolding_amount: str  # "high" (step-by-step hints), "medium", "minimal"
    target_difficulty: int  # 1 to 5


class StudentAdapter:
    """Adapts teaching style based on student profile and historical performance."""

    @staticmethod
    def adapt(profile: Optional[UserProfile] = None, mastery_score: float = 0.5) -> AdaptationStrategy:
        """Calculate adaptation strategy."""
        grade = getattr(profile, "target_class", "11") if profile else "11"
        pref_diff = getattr(profile, "preferred_difficulty", "adaptive") if profile else "adaptive"

        # Determine target difficulty (1 to 5)
        if mastery_score >= 0.8:
            difficulty = 4
            scaffolding = "minimal"
            depth = "deep_dive"
            term_level = "ncert_standard"
            examples = 1
        elif mastery_score >= 0.5:
            difficulty = 3
            scaffolding = "medium"
            depth = "standard"
            term_level = "ncert_standard"
            examples = 2
        else:
            difficulty = 2
            scaffolding = "high"
            depth = "standard"
            term_level = "simplified"
            examples = 2

        logger.info(
            f"Student Adaptation: grade={grade}, mastery={mastery_score:.2f} -> "
            f"difficulty={difficulty}, scaffolding={scaffolding}"
        )

        return AdaptationStrategy(
            response_depth=depth,
            terminology_level=term_level,
            num_examples=examples,
            scaffolding_amount=scaffolding,
            target_difficulty=difficulty,
        )
