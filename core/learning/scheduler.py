"""Spaced Review Scheduler Engine (Phase 5).

Implements evidence-driven spaced review scheduling:
- Initial intervals: 1d -> 3d -> 7d -> 14d -> 30d
- Success (no hints): expand interval
- Hint / Partial: maintain interval
- Failure: reset interval to 1d
- Retention requirement: capping full mastery until delayed recall is verified (P5-T04).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


DEFAULT_INTERVALS: List[int] = [1, 3, 7, 14, 30]


@dataclass
class ReviewScheduleResult:
    concept_id: str
    next_review_at: str
    interval_days: int
    review_count: int
    retention_verified: bool


class SpacedReviewScheduler:
    """Manages spaced review intervals and delayed recall retention enforcement."""

    def __init__(self, intervals: Optional[List[int]] = None):
        self.intervals = intervals or DEFAULT_INTERVALS

    def calculate_next_review(
        self,
        current_interval_days: int,
        correctness: str,
        hint_used: int = 0,
        from_time: Optional[datetime] = None,
    ) -> Tuple[int, str]:
        """Calculate next review interval in days and future ISO timestamp."""
        now = from_time or datetime.now()

        if correctness == 'uncertain':
            next_dt = now + timedelta(days=max(1, current_interval_days))
            return current_interval_days, next_dt.isoformat()

        if correctness == 'incorrect':
            # Reset to 1 day on failure
            new_interval = self.intervals[0]
        elif correctness == 'partially_correct' or hint_used > 0:
            # Maintain current interval on hints or partial correctness
            new_interval = max(self.intervals[0], current_interval_days)
        elif correctness == 'correct':
            # Advance to next interval step
            if current_interval_days <= 0:
                new_interval = self.intervals[0]
            else:
                # Find current step or closest
                idx = 0
                for i, val in enumerate(self.intervals):
                    if current_interval_days >= val:
                        idx = i
                if idx < len(self.intervals) - 1:
                    new_interval = self.intervals[idx + 1]
                else:
                    new_interval = self.intervals[-1] * 2  # Double beyond max step

        next_dt = now + timedelta(days=new_interval)
        return new_interval, next_dt.isoformat()

    def is_review_due(self, next_review_at: str, current_time: Optional[datetime] = None) -> bool:
        """Check if a review is due based on next_review_at ISO string."""
        if not next_review_at:
            return False
        now = current_time or datetime.now()
        try:
            due_dt = datetime.fromisoformat(next_review_at)
            return now >= due_dt
        except ValueError:
            return False

    def update_schedule_and_check_retention(
        self,
        student_id: str,
        concept_id: str,
        correctness: str,
        hint_used: int,
        state_manager: TutorStateManager,
    ) -> ReviewScheduleResult:
        """Update student mastery review schedule and enforce retention requirement (P5-T04)."""
        record = state_manager.get_student_concept_mastery(student_id, concept_id)

        # Parse current interval from next_review_at or default to 1
        current_interval = 1
        if record.next_review_at:
            try:
                due_dt = datetime.fromisoformat(record.next_review_at)
                last_dt = datetime.fromisoformat(record.last_practiced) if record.last_practiced else datetime.now()
                diff_days = (due_dt - last_dt).days
                if diff_days > 0:
                    current_interval = diff_days
            except ValueError:
                current_interval = 1

        new_interval, next_review_str = self.calculate_next_review(current_interval, correctness, hint_used)

        # Check retention verification: requires at least 1 successful review event
        is_review_turn = self.is_review_due(record.next_review_at)
        review_count_delta = 1 if (is_review_turn and correctness == 'correct') else 0

        # We store retention count in exposure/correct counts or via metadata
        # P5-T04: Capping mastery score if retention is not verified
        new_mastery = record.mastery
        retention_verified = (record.correct_count >= 3 and review_count_delta > 0) or (record.mastery < 0.85)

        if not retention_verified and new_mastery >= 0.85:
            # Cap unverified mastery at 0.84 until delayed recall is demonstrated
            new_mastery = 0.84

        with state_manager.conn:
            state_manager.conn.execute('''
                UPDATE student_concept_mastery
                SET next_review_at = ?, mastery = ?
                WHERE student_id = ? AND concept_id = ?
            ''', (next_review_str, new_mastery, student_id, concept_id))

        return ReviewScheduleResult(
            concept_id=concept_id,
            next_review_at=next_review_str,
            interval_days=new_interval,
            review_count=review_count_delta,
            retention_verified=retention_verified,
        )
