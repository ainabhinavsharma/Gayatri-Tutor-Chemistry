"""Tests for Phase 10: Spaced Review (Section 16).

Verifies:
1. Persistence of all 4 required fields:
   - next_review_at
   - interval
   - review_count
   - last_result
2. Configurable schedule progression: 1, 3, 7, 14, 30 days.
3. Schedule adaptation:
   - Failure shortens the interval (resets to 1 day).
   - Independent success extends the interval.
   - Hint-dependent success extends the interval less (maintains current interval).
4. Delayed recall contributes to mastery and caps unverified mastery until retention is demonstrated.
"""
from datetime import datetime, timedelta
import pytest

from core.learning.scheduler import (
    DEFAULT_INTERVALS,
    SpacedReviewScheduler,
    SpacedReviewRecord,
    ReviewScheduleResult,
)
from core.tutor.state import TutorStateManager, LearningEvent


def test_persistence_of_all_four_review_fields(tmp_path):
    """Section 16: Persist next_review_at, interval, review_count, last_result."""
    db_path = str(tmp_path / "test_spaced_persist.db")
    sm = TutorStateManager(db_path)
    scheduler = SpacedReviewScheduler()

    student_id = "student_sr_01"
    concept_id = "chem_thermo_hess"

    # Initial practice event (not a review turn yet)
    result = scheduler.update_schedule_and_check_retention(
        student_id=student_id,
        concept_id=concept_id,
        correctness="correct",
        hint_used=0,
        state_manager=sm,
    )

    # Fetch persisted record
    record = scheduler.get_review_record(student_id, concept_id, sm)
    assert record is not None
    assert record.student_id == student_id
    assert record.concept_id == concept_id
    assert record.next_review_at == result.next_review_at
    assert record.interval == result.interval_days
    assert record.review_count == 0  # Initial turn wasn't a review yet
    assert record.last_result == "correct"
    assert record.updated_at != ""


def test_configurable_schedule_intervals():
    """Section 16: Initial configurable schedule: 1, 3, 7, 14, 30 days."""
    assert DEFAULT_INTERVALS == [1, 3, 7, 14, 30]

    custom_intervals = [2, 5, 10, 20]
    custom_scheduler = SpacedReviewScheduler(intervals=custom_intervals)
    assert custom_scheduler.intervals == [2, 5, 10, 20]

    # Test step advancement with custom schedule
    int_next, _ = custom_scheduler.calculate_next_review(2, correctness="correct", hint_used=0)
    assert int_next == 5


def test_failure_shortens_the_interval(tmp_path):
    """Section 16: Failure shortens the interval."""
    scheduler = SpacedReviewScheduler()

    # If current interval is 7 days, failure shortens it to 1 day
    new_interval, _ = scheduler.calculate_next_review(current_interval_days=7, correctness="incorrect")
    assert new_interval == 1
    assert new_interval < 7

    # If current interval is 14 days, failure shortens it to 1 day
    new_interval_14, _ = scheduler.calculate_next_review(current_interval_days=14, correctness="incorrect")
    assert new_interval_14 == 1
    assert new_interval_14 < 14


def test_independent_success_extends_interval():
    """Section 16: Independent success extends it."""
    scheduler = SpacedReviewScheduler()

    # Step 1 -> 3
    i1, _ = scheduler.calculate_next_review(1, correctness="correct", hint_used=0)
    assert i1 == 3

    # Step 3 -> 7
    i2, _ = scheduler.calculate_next_review(3, correctness="correct", hint_used=0)
    assert i2 == 7

    # Step 7 -> 14
    i3, _ = scheduler.calculate_next_review(7, correctness="correct", hint_used=0)
    assert i3 == 14

    # Step 14 -> 30
    i4, _ = scheduler.calculate_next_review(14, correctness="correct", hint_used=0)
    assert i4 == 30


def test_hint_dependent_success_extends_less():
    """Section 16: Hint-dependent success should extend it less."""
    scheduler = SpacedReviewScheduler()

    # Independent: 3 -> 7
    indep_int, _ = scheduler.calculate_next_review(3, correctness="correct", hint_used=0)
    assert indep_int == 7

    # Hint-dependent: 3 -> 3 (maintained, extends less than independent)
    hint_int, _ = scheduler.calculate_next_review(3, correctness="correct", hint_used=1)
    assert hint_int == 3
    assert hint_int < indep_int

    # Partial: 7 -> 7 (maintained, extends less than independent)
    partial_int, _ = scheduler.calculate_next_review(7, correctness="partially_correct", hint_used=0)
    assert partial_int == 7


def test_delayed_recall_contributes_to_mastery(tmp_path):
    """Section 16: Delayed recall must contribute to mastery (capping unverified mastery)."""
    db_path = str(tmp_path / "test_delayed_recall.db")
    sm = TutorStateManager(db_path)
    scheduler = SpacedReviewScheduler()

    student_id = "student_recall_01"
    concept_id = "chem_inorg_bonding"

    # Set up high initial mastery (0.90) without delayed recall review
    sm.conn.execute('''
        INSERT INTO student_concept_mastery (
            student_id, concept_id, mastery, confidence, exposure_count,
            correct_count, error_count, last_practiced, next_review_at, difficulty_level
        ) VALUES (?, ?, 0.90, 0.8, 5, 4, 1, ?, ?, 3.0)
    ''', (student_id, concept_id, datetime.now().isoformat(), (datetime.now() + timedelta(days=3)).isoformat()))

    # Practice turn before review is due: unverified high mastery is capped at 0.84
    res_capped = scheduler.update_schedule_and_check_retention(
        student_id=student_id,
        concept_id=concept_id,
        correctness="correct",
        hint_used=0,
        state_manager=sm,
    )
    assert res_capped.retention_verified is False
    post_capped_mastery = sm.get_student_concept_mastery(student_id, concept_id).mastery
    assert post_capped_mastery <= 0.84

    # Now make the review due (set next_review_at in the past)
    past_due = (datetime.now() - timedelta(hours=2)).isoformat()
    sm.conn.execute(
        "UPDATE student_concept_mastery SET next_review_at = ? WHERE student_id = ? AND concept_id = ?",
        (past_due, student_id, concept_id)
    )

    # Successful delayed review: retention is verified
    res_verified = scheduler.update_schedule_and_check_retention(
        student_id=student_id,
        concept_id=concept_id,
        correctness="correct",
        hint_used=0,
        state_manager=sm,
    )
    assert res_verified.retention_verified is True
    assert res_verified.review_count >= 1

    rec = scheduler.get_review_record(student_id, concept_id, sm)
    assert rec.review_count >= 1
    assert rec.last_result == "correct"
