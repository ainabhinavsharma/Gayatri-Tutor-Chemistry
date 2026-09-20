"""Tests for Phase 6: Spaced Review Re-Audit (P5-T04)."""
import uuid
from datetime import datetime, timedelta
import pytest
from core.tutor.state import TutorStateManager, LearningEvent
from core.learning.scheduler import SpacedReviewScheduler, DEFAULT_INTERVALS


def test_calculate_next_review_progression():
    """Test interval expansion on correct answers without hints."""
    scheduler = SpacedReviewScheduler()
    now = datetime(2026, 1, 1, 12, 0, 0)

    # 1d -> 3d
    interval, next_at = scheduler.calculate_next_review(1, 'correct', hint_used=0, from_time=now)
    assert interval == 3
    assert next_at == (now + timedelta(days=3)).isoformat()

    # 3d -> 7d
    interval, next_at = scheduler.calculate_next_review(3, 'correct', hint_used=0, from_time=now)
    assert interval == 7

    # 7d -> 14d
    interval, next_at = scheduler.calculate_next_review(7, 'correct', hint_used=0, from_time=now)
    assert interval == 14

    # 14d -> 30d
    interval, next_at = scheduler.calculate_next_review(14, 'correct', hint_used=0, from_time=now)
    assert interval == 30

    # 30d -> 60d (double beyond max step)
    interval, next_at = scheduler.calculate_next_review(30, 'correct', hint_used=0, from_time=now)
    assert interval == 60


def test_calculate_next_review_hint_and_failure():
    """Test interval maintenance on hints and reset on failure."""
    scheduler = SpacedReviewScheduler()
    now = datetime(2026, 1, 1, 12, 0, 0)

    # Hint used maintains current interval
    interval, next_at = scheduler.calculate_next_review(7, 'correct', hint_used=1, from_time=now)
    assert interval == 7

    # Partially correct maintains current interval
    interval, next_at = scheduler.calculate_next_review(14, 'partially_correct', hint_used=0, from_time=now)
    assert interval == 14

    # Incorrect resets interval to 1 day
    interval, next_at = scheduler.calculate_next_review(14, 'incorrect', hint_used=0, from_time=now)
    assert interval == 1

    # Uncertain maintains interval
    interval, next_at = scheduler.calculate_next_review(7, 'uncertain', hint_used=0, from_time=now)
    assert interval == 7


def test_is_review_due():
    """Test due date evaluation logic."""
    scheduler = SpacedReviewScheduler()
    now = datetime(2026, 1, 10, 12, 0, 0)

    # Past date is due
    past_str = (now - timedelta(days=1)).isoformat()
    assert scheduler.is_review_due(past_str, current_time=now) is True

    # Exact current time is due
    exact_str = now.isoformat()
    assert scheduler.is_review_due(exact_str, current_time=now) is True

    # Future date is not due
    future_str = (now + timedelta(days=1)).isoformat()
    assert scheduler.is_review_due(future_str, current_time=now) is False

    # Empty string or invalid format is not due
    assert scheduler.is_review_due("", current_time=now) is False
    assert scheduler.is_review_due("invalid_date", current_time=now) is False


def test_update_schedule_and_retention_capping(tmp_path):
    """Test updating database schedule and retention mastery capping (>= 0.85 capped at 0.84 if unverified)."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    scheduler = SpacedReviewScheduler()

    # Record initial learning event with high mastery 0.90 but low correct_count (1)
    event = LearningEvent(
        event_id=str(uuid.uuid4()),
        student_id="student_review_1",
        session_id="sess_1",
        turn_id="turn_1",
        concept_id="thermo.hess",
        correctness="correct",
        hint_used=0,
    )
    sm.record_learning_event(event)

    # Manually set mastery to 0.90 to simulate unverified high mastery
    with sm.conn:
        sm.conn.execute(
            "UPDATE student_concept_mastery SET mastery = 0.90 WHERE student_id = ? AND concept_id = ?",
            ("student_review_1", "thermo.hess")
        )

    # Run scheduler update (unverified retention because correct_count < 3 and review not due)
    res = scheduler.update_schedule_and_check_retention(
        student_id="student_review_1",
        concept_id="thermo.hess",
        correctness="correct",
        hint_used=0,
        state_manager=sm,
    )

    assert res.retention_verified is False
    # Verify mastery in DB was capped at 0.84
    record = sm.get_student_concept_mastery("student_review_1", "thermo.hess")
    assert record.mastery == 0.84
    assert record.next_review_at != ""


def test_verified_retention_high_mastery(tmp_path):
    """Test that verified retention preserves high mastery score (>= 0.85)."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    scheduler = SpacedReviewScheduler()

    # Simulate 3 prior correct practices
    for i in range(3):
        event = LearningEvent(
            event_id=str(uuid.uuid4()),
            student_id="student_review_2",
            session_id="sess_2",
            turn_id=f"turn_{i}",
            concept_id="inorganic.periodic",
            correctness="correct",
            hint_used=0,
        )
        sm.record_learning_event(event)

    # Manually set mastery to 0.90
    with sm.conn:
        sm.conn.execute(
            "UPDATE student_concept_mastery SET mastery = 0.90 WHERE student_id = ? AND concept_id = ?",
            ("student_review_2", "inorganic.periodic")
        )

    # Set due date in the past so it counts as a review turn
    past_due = (datetime.now() - timedelta(hours=2)).isoformat()
    with sm.conn:
        sm.conn.execute(
            "UPDATE student_concept_mastery SET next_review_at = ? WHERE student_id = ? AND concept_id = ?",
            (past_due, "student_review_2", "inorganic.periodic")
        )

    res = scheduler.update_schedule_and_check_retention(
        student_id="student_review_2",
        concept_id="inorganic.periodic",
        correctness="correct",
        hint_used=0,
        state_manager=sm,
    )

    assert res.retention_verified is True
    record = sm.get_student_concept_mastery("student_review_2", "inorganic.periodic")
    assert record.mastery == 0.90
