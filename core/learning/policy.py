"""Adaptive Difficulty Policy Engine (P4-T02).

Manages question difficulty level (1 to 5) based on persisted evidence:
- 2+ consecutive independent correct answers -> increase (+1)
- Correct with hint -> maintain
- Partial -> maintain/reduce
- Conceptual error -> reduce (-1)
- 2 consecutive conceptual errors -> trigger prerequisite review signal
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from core.tutor.state import LearningEvent


DIFFICULTY_LEVELS = {
    1: "Recall",
    2: "Basic",
    3: "Standard",
    4: "Multi-step",
    5: "Advanced",
}


def get_difficulty_label(level: int) -> str:
    """Return the pedagogical label for difficulty levels 1 to 5."""
    clamped = max(1, min(5, int(round(level))))
    return DIFFICULTY_LEVELS.get(clamped, "Standard")


@dataclass
class DifficultyDecision:
    new_difficulty: int
    action: str  # 'increase', 'maintain', 'reduce', 'prerequisite_review'
    reason: str
    recommend_prerequisite_review: bool = False
    difficulty_label: str = ""

    def __post_init__(self):
        if not self.difficulty_label:
            self.difficulty_label = get_difficulty_label(self.new_difficulty)


class DifficultyPolicy:
    """Deterministic evidence-driven difficulty adjustment policy."""

    MIN_DIFFICULTY: int = 1
    MAX_DIFFICULTY: int = 5

    def evaluate_next_difficulty(
        self,
        events: List[LearningEvent],
        current_difficulty: int = 3,
    ) -> DifficultyDecision:
        """Evaluate evidence history to decide the next difficulty level."""
        # Ensure input level is integer 1..5
        if isinstance(current_difficulty, float):
            if current_difficulty <= 1.0:
                current_difficulty = int(round(current_difficulty * 5.0))
            else:
                current_difficulty = int(round(current_difficulty))
        current_difficulty = max(self.MIN_DIFFICULTY, min(self.MAX_DIFFICULTY, current_difficulty))

        valid_events = [e for e in events if e.correctness != 'uncertain']
        if not valid_events:
            return DifficultyDecision(
                new_difficulty=current_difficulty,
                action='maintain',
                reason='No valid learning evidence yet.',
                recommend_prerequisite_review=False,
            )

        recent = valid_events[-2:]

        # Rule 1: Check for 2 consecutive conceptual errors -> Prerequisite review
        if len(recent) >= 2 and all(e.correctness == 'incorrect' for e in recent):
            new_diff = max(self.MIN_DIFFICULTY, current_difficulty - 1)
            return DifficultyDecision(
                new_difficulty=new_diff,
                action='prerequisite_review',
                reason='Two consecutive conceptual errors detected; triggering prerequisite review.',
                recommend_prerequisite_review=True,
            )

        last_event = valid_events[-1]

        # Rule 2: Single conceptual error -> Reduce difficulty
        if last_event.correctness == 'incorrect':
            new_diff = max(self.MIN_DIFFICULTY, current_difficulty - 1)
            return DifficultyDecision(
                new_difficulty=new_diff,
                action='reduce',
                reason='Conceptual error on last attempt; reducing difficulty level.',
                recommend_prerequisite_review=False,
            )

        # Rule 3: Correct with hint -> Maintain difficulty (hint dependency)
        if last_event.correctness == 'correct' and last_event.hint_used > 0:
            return DifficultyDecision(
                new_difficulty=current_difficulty,
                action='maintain',
                reason='Correct answer required a hint; maintaining current difficulty level.',
                recommend_prerequisite_review=False,
            )

        # Rule 4: Partially correct -> Maintain or reduce
        if last_event.correctness == 'partially_correct':
            return DifficultyDecision(
                new_difficulty=current_difficulty,
                action='maintain',
                reason='Partially correct answer; maintaining current difficulty level.',
                recommend_prerequisite_review=False,
            )

        # Rule 5: 2+ consecutive independent correct answers -> Increase difficulty
        if len(recent) >= 2 and all(e.correctness == 'correct' and e.hint_used == 0 for e in recent):
            new_diff = min(self.MAX_DIFFICULTY, current_difficulty + 1)
            action = 'increase' if new_diff > current_difficulty else 'maintain'
            return DifficultyDecision(
                new_difficulty=new_diff,
                action=action,
                reason='Two consecutive independent correct answers; increasing difficulty level.',
                recommend_prerequisite_review=False,
            )

        # Default fallback: Maintain current difficulty
        return DifficultyDecision(
            new_difficulty=current_difficulty,
            action='maintain',
            reason='Single independent correct answer; continuing at current difficulty level.',
            recommend_prerequisite_review=False,
        )
