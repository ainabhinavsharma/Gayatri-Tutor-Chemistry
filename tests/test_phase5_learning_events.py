"""Tests for Phase 5: Learning-Event Integrity.

Verifies:
1. LearningEvent contains all 11 required fields.
2. Duplicate event processing is idempotent (state changes exactly once).
3. Replaying the same event 5 times causes zero extra mutations.
4. Learning evidence is durable and queryable via get_learning_events.
5. LearningEventStream correctly filters and computes statistics.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from dataclasses import fields

from core.tutor.state import TutorStateManager, LearningEvent
from core.learning.events import LearningEventStream


def test_learning_event_schema_11_fields():
    """Verify LearningEvent contains all 11 required fields."""
    required_fields = {
        "event_id",
        "student_id",
        "session_id",
        "turn_id",
        "concept_id",
        "question_id",
        "timestamp",
        "correctness",
        "difficulty",
        "hint_used",
    }
    actual_fields = {f.name for f in fields(LearningEvent)}
    assert required_fields.issubset(actual_fields)

    # Verify misconception attribute/property exists
    ev = LearningEvent(
        event_id="test_ev",
        student_id="student_1",
        session_id="sess_1",
        turn_id="turn_1",
        concept_id="chem_thermo_system",
        misconception_code="THERMO_SIGN_CONVENTION"
    )
    assert hasattr(ev, "misconception")
    assert ev.misconception == "THERMO_SIGN_CONVENTION"
    assert "misconception" in ev.to_dict()


def test_duplicate_event_idempotency(tmp_path):
    """Verify submitting the same event twice changes state exactly once."""
    db_file = tmp_path / "test_idempotency.db"
    manager = TutorStateManager(db_path=db_file)

    student_id = "student_alpha"
    concept_id = "chem_thermo_first_law"

    ev = LearningEvent(
        event_id="ev_unique_100",
        student_id=student_id,
        session_id="sess_100",
        turn_id="turn_100",
        concept_id=concept_id,
        question_id="q_1",
        correctness="correct",
        difficulty=0.5,
        hint_used=0
    )

    # First submission -> True
    first_res = manager.record_learning_event(ev)
    assert first_res is True

    mastery_first = manager.get_student_concept_mastery(student_id, concept_id)
    assert mastery_first.exposure_count == 1
    assert mastery_first.correct_count == 1
    assert mastery_first.mastery == 0.1

    # Second submission with identical event_id -> False
    second_res = manager.record_learning_event(ev)
    assert second_res is False

    # State must remain identical (no double counting!)
    mastery_second = manager.get_student_concept_mastery(student_id, concept_id)
    assert mastery_second.exposure_count == 1
    assert mastery_second.correct_count == 1
    assert mastery_second.mastery == 0.1


def test_repeated_replay_no_drift(tmp_path):
    """Verify replaying the same event 5 times causes zero drift or mutation."""
    db_file = tmp_path / "test_replay.db"
    manager = TutorStateManager(db_path=db_file)

    student_id = "student_beta"
    concept_id = "chem_thermo_enthalpy"

    ev = LearningEvent(
        event_id="ev_replay_200",
        student_id=student_id,
        session_id="sess_200",
        turn_id="turn_200",
        concept_id=concept_id,
        question_id="q_2",
        correctness="incorrect",
        difficulty=0.5,
        hint_used=1
    )

    # Initial record
    assert manager.record_learning_event(ev) is True

    # Replay 5 times
    for _ in range(5):
        assert manager.record_learning_event(ev) is False

    mastery = manager.get_student_concept_mastery(student_id, concept_id)
    assert mastery.exposure_count == 1
    assert mastery.error_count == 1
    assert mastery.hint_count == 1


def test_evidence_durability_and_query(tmp_path):
    """Verify that learning evidence is durably persisted and queryable."""
    db_file = tmp_path / "test_durability.db"
    manager = TutorStateManager(db_path=db_file)

    student_id = "student_gamma"
    concept_id = "chem_inorg_periodic"

    ev1 = LearningEvent(
        event_id="ev_durable_1",
        student_id=student_id,
        session_id="sess_1",
        turn_id="turn_1",
        concept_id=concept_id,
        correctness="correct",
        difficulty=0.3,
        misconception_code=""
    )
    ev2 = LearningEvent(
        event_id="ev_durable_2",
        student_id=student_id,
        session_id="sess_1",
        turn_id="turn_2",
        concept_id=concept_id,
        correctness="incorrect",
        difficulty=0.4,
        misconception_code="PERIODIC_TREND_CONFUSION"
    )

    manager.record_learning_event(ev1)
    manager.record_learning_event(ev2)

    # Query events from database
    persisted_events = manager.get_learning_events(student_id, concept_id)
    assert len(persisted_events) == 2
    assert persisted_events[0].event_id == "ev_durable_1"
    assert persisted_events[1].event_id == "ev_durable_2"
    assert persisted_events[1].misconception == "PERIODIC_TREND_CONFUSION"

    # Verify stream analysis
    accuracy = LearningEventStream.calculate_recent_accuracy(persisted_events)
    assert accuracy == 0.5  # 1 correct, 1 incorrect
