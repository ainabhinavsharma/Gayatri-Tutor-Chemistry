"""Gayatri AI — Adaptive Test Selector (P7-T09).

Selects questions dynamically based on student topic mastery and recent accuracy.
"""
from __future__ import annotations

import logging
from typing import Optional

from core.assessment.schema import Question

logger = logging.getLogger("gayatri.assessment.adaptive")


class AdaptiveTestSelector:
    """Selects questions adaptively using performance signals."""

    @staticmethod
    def select_next_question(
        available_questions: list[Question],
        mastery_score: float = 0.5,
        recent_correctness: bool = True,
    ) -> Optional[Question]:
        """Select question matching student's current mastery level."""
        if not available_questions:
            return None

        target_diff = 3
        if mastery_score >= 0.8:
            target_diff = 4 if recent_correctness else 3
        elif mastery_score <= 0.4:
            target_diff = 2 if recent_correctness else 1

        # Find closest difficulty match
        best_q = min(available_questions, key=lambda q: abs(q.difficulty - target_diff))
        logger.info(
            f"Adaptive Selection: target_difficulty={target_diff}, "
            f"selected_q={best_q.question_id} (diff={best_q.difficulty})"
        )
        return best_q
