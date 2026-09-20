"""Tests for Phase 12: Learning Progress Re-Audit (P9-T01 to P9-T05)."""
import uuid
import pytest
from core.tutor.state import TutorStateManager, LearningEvent
from core.learning.progress import ProgressService, get_status_label
from core.learning.misconceptions import MisconceptionTracker


def test_status_label_computation():
    """Test standard progress status label computation rules."""
    # REVIEW_DUE when due and exposure > 0
    assert get_status_label(0.90, 5, is_due=True) == "REVIEW_DUE"

    # NEW when exposure == 0
    assert get_status_label(0.0, 0, is_due=False) == "NEW"

    # LEARNING when exposure < 3
    assert get_status_label(0.5, 2, is_due=False) == "LEARNING"

    # MASTERED when mastery >= 0.85 and exposure >= 3
    assert get_status_label(0.85, 4, is_due=False) == "MASTERED"
    assert get_status_label(0.92, 5, is_due=False) == "MASTERED"

    # PROFICIENT when 0.70 <= mastery < 0.85 and exposure >= 3
    assert get_status_label(0.75, 4, is_due=False) == "PROFICIENT"

    # PRACTICING when mastery < 0.70 and exposure >= 3
    assert get_status_label(0.60, 4, is_due=False) == "PRACTICING"


def test_get_concept_progress(tmp_path):
    """Test detailed concept progress retrieval and misconception inclusion."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    service = ProgressService(state_manager=sm)

    # Seed 3 learning events for a concept
    for i in range(3):
        event = LearningEvent(
            event_id=f"evt_prog_{i}",
            student_id="student_prog_1",
            session_id="sess_prog_1",
            turn_id=f"turn_prog_{i}",
            concept_id="thermo.hess_law",
            correctness="correct" if i < 2 else "incorrect",
        )
        sm.record_learning_event(event)

    # Seed a misconception
    tracker = MisconceptionTracker(sm)
    tracker.record_misconception("student_prog_1", "thermo.hess_law", "HESS_LAW_DIRECTION")

    progress = service.get_concept_progress("student_prog_1", "thermo.hess_law")
    assert progress["student_id"] == "student_prog_1"
    assert progress["concept_id"] == "thermo.hess_law"
    assert progress["domain"] == "Thermodynamics"
    assert progress["exposure_count"] == 3
    assert progress["correct_count"] == 2
    assert progress["error_count"] == 1
    assert progress["accuracy"] == 0.6667
    assert "HESS_LAW_DIRECTION" in progress["active_misconceptions"]


def test_get_student_progress_summary(tmp_path):
    """Test overall and domain-level student progress summary."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    service = ProgressService(state_manager=sm)

    # Seed learning events in Thermodynamics & Inorganic Chemistry
    event1 = LearningEvent(
        event_id="evt_sum_1",
        student_id="student_prog_2",
        session_id="sess_sum_1",
        turn_id="turn_sum_1",
        concept_id="thermo.first_law",
        correctness="correct",
    )
    event2 = LearningEvent(
        event_id="evt_sum_2",
        student_id="student_prog_2",
        session_id="sess_sum_1",
        turn_id="turn_sum_2",
        concept_id="inorganic.periodicity",
        correctness="correct",
    )
    sm.record_learning_event(event1)
    sm.record_learning_event(event2)

    summary = service.get_student_progress_summary("student_prog_2")
    assert summary["student_id"] == "student_prog_2"
    assert summary["total_concepts_tracked"] >= 2
    assert "Thermodynamics" in summary["domain_mastery"]
    assert "Inorganic Chemistry" in summary["domain_mastery"]
    assert summary["overall_mastery"] >= 0.0
