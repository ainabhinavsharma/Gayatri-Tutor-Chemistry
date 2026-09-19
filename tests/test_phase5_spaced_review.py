"""Phase 5 Test Suite: Spaced Review Engine.

Verifies review scheduling interval progression, retention requirement enforcement,
and due review detection (P5-T01 through P5-T04).
"""
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from core.learning.scheduler import SpacedReviewScheduler
from core.tutor.state import StudentConceptMastery, TutorStateManager


@pytest.fixture
def temp_state_manager():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    sm = TutorStateManager(db_path=db_path)
    yield sm
    try:
        Path(db_path).unlink()
    except Exception:
        pass


def test_interval_progression_success():
    scheduler = SpacedReviewScheduler()

    # Initial success: 1d -> 3d
    interval, next_ts = scheduler.calculate_next_review(1, correctness='correct', hint_used=0)
    assert interval == 3

    # Success from 3d -> 7d
    interval, next_ts = scheduler.calculate_next_review(3, correctness='correct', hint_used=0)
    assert interval == 7

    # Success from 7d -> 14d
    interval, next_ts = scheduler.calculate_next_review(7, correctness='correct', hint_used=0)
    assert interval == 14

    # Success from 14d -> 30d
    interval, next_ts = scheduler.calculate_next_review(14, correctness='correct', hint_used=0)
    assert interval == 30


def test_interval_hint_and_failure():
    scheduler = SpacedReviewScheduler()

    # Hint used -> maintain interval (7d -> 7d)
    interval, next_ts = scheduler.calculate_next_review(7, correctness='correct', hint_used=1)
    assert interval == 7

    # Failure -> reset to 1d (30d -> 1d)
    interval, next_ts = scheduler.calculate_next_review(30, correctness='incorrect')
    assert interval == 1


def test_is_review_due():
    scheduler = SpacedReviewScheduler()

    past_ts = (datetime.now() - timedelta(days=1)).isoformat()
    future_ts = (datetime.now() + timedelta(days=2)).isoformat()

    assert scheduler.is_review_due(past_ts) is True
    assert scheduler.is_review_due(future_ts) is False
    assert scheduler.is_review_due('') is False


def test_retention_capping(temp_state_manager):
    scheduler = SpacedReviewScheduler()

    # Setup student with mastery 0.90 but no retention review yet
    temp_state_manager.conn.execute('''
        INSERT INTO student_concept_mastery (student_id, concept_id, mastery, correct_count)
        VALUES ('student_ret', 'thermo.hess', 0.90, 1)
    ''')

    result = scheduler.update_schedule_and_check_retention(
        student_id='student_ret',
        concept_id='thermo.hess',
        correctness='correct',
        hint_used=0,
        state_manager=temp_state_manager,
    )

    record_after = temp_state_manager.get_student_concept_mastery('student_ret', 'thermo.hess')
    assert record_after.mastery == 0.84
    assert result.retention_verified is False
