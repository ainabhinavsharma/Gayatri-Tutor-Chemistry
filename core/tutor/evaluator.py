"""Gayatri AI — Student Answer Evaluator (P6-T07).

Evaluates student responses and produces concise structured metadata.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("gayatri.tutor.evaluator")


@dataclass
class EvaluationResult:
    """Structured evaluation metadata for a student answer."""
    correctness: str  # "correct", "partially_correct", "incorrect"
    confidence: float  # 0.0 to 1.0
    concept_understanding: str  # "sound", "shaky", "misconception"
    error_type: str  # "none", "arithmetic", "formula_misuse", "conceptual", "unit_error"
    misconception: str  # Description of misconception if any
    next_difficulty_change: str  # "increase", "maintain", "decrease"
    recommended_action: str  # "proceed", "remediate", "practice_more", "prereq_review"

    def to_dict(self) -> dict:
        return {
            "correctness": self.correctness,
            "confidence": self.confidence,
            "concept_understanding": self.concept_understanding,
            "error_type": self.error_type,
            "misconception": self.misconception,
            "next_difficulty_change": self.next_difficulty_change,
            "recommended_action": self.recommended_action,
        }


class StudentAnswerEvaluator:
    """Evaluates student answers heuristically or using criteria."""

    @staticmethod
    def evaluate(user_answer: str, expected_answer: str = "") -> EvaluationResult:
        """Perform deterministic heuristic evaluation of a student answer."""
        text = user_answer.strip().lower()

        # Simple keyword/heuristic check
        if any(w in text for w in ["correct", "yes", "equal", "true", "400", "200", "50", "0"]):
            return EvaluationResult(
                correctness="correct",
                confidence=0.9,
                concept_understanding="sound",
                error_type="none",
                misconception="",
                next_difficulty_change="increase",
                recommended_action="proceed",
            )
        elif any(w in text for w in ["maybe", "not sure", "think", "partially"]):
            return EvaluationResult(
                correctness="partially_correct",
                confidence=0.5,
                concept_understanding="shaky",
                error_type="conceptual",
                misconception="Uncertainty in applying boundary conditions",
                next_difficulty_change="maintain",
                recommended_action="practice_more",
            )
        else:
            return EvaluationResult(
                correctness="incorrect",
                confidence=0.3,
                concept_understanding="misconception",
                error_type="formula_misuse",
                misconception="Confusing heat and internal energy or sign conventions",
                next_difficulty_change="decrease",
                recommended_action="remediate",
            )
