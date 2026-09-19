"""Evidence-driven Mastery Engine (P4-T01).

Calculates student concept mastery from persisted learning evidence using a transparent, multi-factor model:
mastery = 0.45 * recent_accuracy
        + 0.25 * long_term_accuracy
        + 0.15 * difficulty_adjusted_score
        + 0.10 * independent_success
        + 0.05 * retention_score
Clamped 0.0 <= mastery <= 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.tutor.state import LearningEvent, StudentConceptMastery, TutorStateManager


@dataclass
class MasteryWeights:
    recent_accuracy: float = 0.45
    long_term_accuracy: float = 0.25
    difficulty_adjusted: float = 0.15
    independent_success: float = 0.10
    retention_score: float = 0.05


class MasteryCalculator:
    """Calculates student mastery transparently based on evidence records."""

    def __init__(self, weights: Optional[MasteryWeights] = None):
        self.weights = weights or MasteryWeights()

    def _event_accuracy(self, correctness: str) -> float:
        if correctness == 'correct':
            return 1.0
        elif correctness == 'partially_correct':
            return 0.5
        elif correctness == 'incorrect':
            return 0.0
        return 0.0  # uncertain is filtered before this or scores 0

    def compute_mastery(self, events: List[LearningEvent]) -> float:
        """Compute mastery score (0.0 to 1.0) from a list of learning events."""
        valid_events = [e for e in events if e.correctness != 'uncertain']
        if not valid_events:
            return 0.0

        # 1. Recent accuracy (last 5 events)
        recent_events = valid_events[-5:]
        recent_acc = sum(self._event_accuracy(e.correctness) for e in recent_events) / len(recent_events)

        # 2. Long-term accuracy (all valid events)
        long_term_acc = sum(self._event_accuracy(e.correctness) for e in valid_events) / len(valid_events)

        # 3. Difficulty-adjusted score
        # Normalize difficulty: level scale 1..5 -> 0.2..1.0
        diff_scores = []
        for e in valid_events:
            acc = self._event_accuracy(e.correctness)
            diff_norm = e.difficulty if e.difficulty <= 1.0 else e.difficulty / 5.0
            diff_scores.append(acc * diff_norm)
        difficulty_score = sum(diff_scores) / len(diff_scores)

        # 4. Independent success (fraction of correct answers given without hints)
        correct_events = [e for e in valid_events if e.correctness == 'correct']
        if correct_events:
            independent_count = sum(1 for e in correct_events if e.hint_used == 0)
            independent_success = independent_count / len(correct_events)
        else:
            independent_success = 0.0

        # 5. Retention score (accuracy on review / delayed practice events)
        review_events = [e for e in valid_events if e.source in ('review', 'spaced_review', 'assessment')]
        if review_events:
            retention_score = sum(self._event_accuracy(e.correctness) for e in review_events) / len(review_events)
        else:
            retention_score = long_term_acc  # Default fallback if no explicit review events yet

        # Weighted sum calculation
        raw_mastery = (
            self.weights.recent_accuracy * recent_acc +
            self.weights.long_term_accuracy * long_term_acc +
            self.weights.difficulty_adjusted * difficulty_score +
            self.weights.independent_success * independent_success +
            self.weights.retention_score * retention_score
        )

        return max(0.0, min(1.0, round(raw_mastery, 4)))

    def update_student_mastery_state(
        self,
        student_id: str,
        concept_id: str,
        events: List[LearningEvent],
        state_manager: TutorStateManager,
    ) -> StudentConceptMastery:
        """Calculate mastery from evidence and update persistent state_manager database."""
        current = state_manager.get_student_concept_mastery(student_id, concept_id)
        new_mastery = self.compute_mastery(events)

        valid_events = [e for e in events if e.correctness != 'uncertain']
        correct_count = sum(1 for e in valid_events if e.correctness == 'correct')
        error_count = sum(1 for e in valid_events if e.correctness == 'incorrect')
        exposure_count = len(valid_events)

        # Confidence is derived from number of evidence samples
        confidence = min(1.0, round(exposure_count / 10.0, 2))

        latest_diff = events[-1].difficulty if events else current.difficulty_level

        state_manager.conn.execute('''
            INSERT INTO student_concept_mastery (
                student_id, concept_id, mastery, confidence, exposure_count,
                correct_count, error_count, last_practiced, next_review_at, difficulty_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, concept_id) DO UPDATE SET
                mastery = excluded.mastery,
                confidence = excluded.confidence,
                exposure_count = excluded.exposure_count,
                correct_count = excluded.correct_count,
                error_count = excluded.error_count,
                last_practiced = excluded.last_practiced,
                difficulty_level = excluded.difficulty_level
        ''', (
            student_id, concept_id, new_mastery, confidence, exposure_count,
            correct_count, error_count, current.last_practiced, current.next_review_at, latest_diff
        ))

        return state_manager.get_student_concept_mastery(student_id, concept_id)
