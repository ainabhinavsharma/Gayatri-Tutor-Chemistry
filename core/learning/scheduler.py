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
class SpacedReviewRecord:
    """Persisted spaced review state (Section 16)."""
    student_id: str
    concept_id: str
    next_review_at: str
    interval: int
    review_count: int
    last_result: str
    updated_at: str


@dataclass
class ReviewScheduleResult:
    concept_id: str
    next_review_at: str
    interval_days: int
    review_count: int
    retention_verified: bool


class SpacedReviewScheduler:
    """Manages spaced review intervals and delayed recall retention enforcement (Section 16)."""

    def __init__(self, intervals: Optional[List[int]] = None):
        self.intervals = intervals or DEFAULT_INTERVALS

    def _ensure_table_exists(self, conn) -> None:
        """Ensure student_spaced_reviews table exists for persistent tracking."""
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS student_spaced_reviews (
                    student_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    next_review_at TEXT NOT NULL,
                    interval INTEGER DEFAULT 1,
                    review_count INTEGER DEFAULT 0,
                    last_result TEXT DEFAULT '',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (student_id, concept_id)
                );
            ''')

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
            # Failure shortens interval: reset to 1 day
            new_interval = self.intervals[0]
        elif correctness == 'partially_correct' or hint_used > 0:
            # Hint-dependent / partial success extends less: maintain current interval
            new_interval = max(self.intervals[0], current_interval_days)
        elif correctness == 'correct':
            # Independent success extends interval along schedule [1, 3, 7, 14, 30]
            if current_interval_days <= 0:
                new_interval = self.intervals[0]
            else:
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

    def get_review_record(
        self,
        student_id: str,
        concept_id: str,
        state_manager: TutorStateManager,
    ) -> Optional[SpacedReviewRecord]:
        """Retrieve persisted spaced review tracking record for a student concept."""
        if not state_manager:
            return None
        self._ensure_table_exists(state_manager.conn)
        cursor = state_manager.conn.execute(
            'SELECT * FROM student_spaced_reviews WHERE student_id = ? AND concept_id = ?',
            (student_id, concept_id)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SpacedReviewRecord(
            student_id=row['student_id'],
            concept_id=row['concept_id'],
            next_review_at=row['next_review_at'],
            interval=row['interval'],
            review_count=row['review_count'],
            last_result=row['last_result'],
            updated_at=row['updated_at'],
        )

    def update_schedule_and_check_retention(
        self,
        student_id: str,
        concept_id: str,
        correctness: str,
        hint_used: int,
        state_manager: TutorStateManager,
    ) -> ReviewScheduleResult:
        """Update student mastery review schedule and enforce retention requirement (Section 16)."""
        self._ensure_table_exists(state_manager.conn)
        record = state_manager.get_student_concept_mastery(student_id, concept_id)

        # Query existing spaced review record if any
        prev_record = self.get_review_record(student_id, concept_id, state_manager)
        if prev_record:
            current_interval = prev_record.interval
            accumulated_review_count = prev_record.review_count
        else:
            current_interval = 1
            accumulated_review_count = 0
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

        # Check review turn & increment review_count if this was a review
        is_review_turn = self.is_review_due(record.next_review_at)
        new_review_count = accumulated_review_count + (1 if is_review_turn else 0)

        # Retention requirement: requires successful review before mastery >= 0.85
        retention_verified = (record.correct_count >= 3 and new_review_count > 0) or (record.mastery < 0.85)
        new_mastery = record.mastery
        if not retention_verified and new_mastery >= 0.85:
            new_mastery = 0.84

        now_str = datetime.now().isoformat()
        with state_manager.conn:
            state_manager.conn.execute('''
                INSERT INTO student_spaced_reviews (
                    student_id, concept_id, next_review_at, interval,
                    review_count, last_result, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, concept_id) DO UPDATE SET
                    next_review_at = excluded.next_review_at,
                    interval = excluded.interval,
                    review_count = excluded.review_count,
                    last_result = excluded.last_result,
                    updated_at = excluded.updated_at
            ''', (
                student_id, concept_id, next_review_str, new_interval,
                new_review_count, correctness, now_str
            ))

            state_manager.conn.execute('''
                UPDATE student_concept_mastery
                SET next_review_at = ?, mastery = ?
                WHERE student_id = ? AND concept_id = ?
            ''', (next_review_str, new_mastery, student_id, concept_id))

        return ReviewScheduleResult(
            concept_id=concept_id,
            next_review_at=next_review_str,
            interval_days=new_interval,
            review_count=new_review_count,
            retention_verified=retention_verified,
        )
