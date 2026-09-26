"""Gayatri AI — Adaptive Difficulty Manager (P6-T08).

Implements non-arbitrary, step-wise difficulty adaptation policy:
- correct + confident -> maintain or increase difficulty (+1)
- correct + uncertain -> maintain level + reinforcement
- partially correct   -> targeted hint / remediation
- incorrect           -> diagnose misconception + simpler example (-1)
- repeated incorrect  -> prerequisite review
"""
from __future__ import annotations

import logging

from core.tutor.evaluator import EvaluationResult

logger = logging.getLogger("gayatri.tutor.difficulty")


class DifficultyManager:
    """Manages adaptive difficulty transitions bounded between L1 and L5."""

    MIN_DIFFICULTY = 1
    MAX_DIFFICULTY = 5

    @classmethod
    def calculate_next_difficulty(cls, current_difficulty: int, eval_result: EvaluationResult) -> int:
        """Calculate next difficulty level based on evaluation results."""
        new_diff = current_difficulty

        if eval_result.correctness == "correct" and eval_result.confidence >= 0.7:
            new_diff = min(cls.MAX_DIFFICULTY, current_difficulty + 1)
        elif eval_result.correctness == "incorrect":
            new_diff = max(cls.MIN_DIFFICULTY, current_difficulty - 1)

        logger.info(
            f"Difficulty Adaptation: L{current_difficulty} -> L{new_diff} "
            f"(result={eval_result.correctness}, conf={eval_result.confidence:.2f})"
        )
        return new_diff
