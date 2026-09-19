"""Gayatri AI - Phase 1 Acceptance Test Suite.

Tests student-scoped learning state isolation, append-only learning events,
turn IDs, idempotency, mode isolation invariants, and migration 204 fields.
"""

import pytest
import uuid
from pathlib import Path
from core.tutor.state import (
    TutorStateManager,
    StudentConceptMastery,
    LearningEvent,
    generate_turn_id,
)


@pytest.fixture
def tutor_mgr(tmp_path):
    db_file = tmp_path / "test_phase1.db"
    return TutorStateManager(db_path=db_file)


def test_student_mastery_isolated(tutor_mgr):
    '''P1-T01: Verify Student A's mastery update does not affect Student B.'''
    turn_a, ts_a = generate_turn_id("student_A", "session_1")
    turn_b, ts_b = generate_turn_id("student_B", "session_1")

    event_a = LearningEvent(
        event_id=str(uuid.uuid4()),
        student_id="student_A",
        session_id="session_1",
        turn_id=turn_a,
        concept_id="chem_thermo_first_law",
        correctness="correct",
    )
    assert tutor_mgr.record_learning_event(event_a) is True

    mastery_a = tutor_mgr.get_student_concept_mastery("student_A", "chem_thermo_first_law")
    mastery_b = tutor_mgr.get_student_concept_mastery("student_B", "chem_thermo_first_law")

    assert mastery_a.mastery > 0.0
    assert mastery_a.exposure_count == 1
    assert mastery_b.mastery == 0.0
    assert mastery_b.exposure_count == 0


def test_learning_event_unique(tutor_mgr):
    '''P1-T03 & P1-T04: Verify turn IDs and learning events are unique and recorded.'''
    turn_id, ts = generate_turn_id("student_A", "session_100")
    assert turn_id.startswith("turn_")
    assert len(ts) > 0

    event_1 = LearningEvent(
        event_id="evt_001",
        student_id="student_A",
        session_id="session_100",
        turn_id=turn_id,
        concept_id="chem_thermo_enthalpy",
        correctness="correct",
    )
    assert tutor_mgr.record_learning_event(event_1) is True


def test_duplicate_event_is_idempotent(tutor_mgr):
    '''P1-T05: Verify re-recording the same learning_event_id is idempotent.'''
    event_dup = LearningEvent(
        event_id="evt_idempotent_123",
        student_id="student_A",
        session_id="session_1",
        turn_id="turn_001",
        concept_id="chem_inorg_periodic",
        correctness="correct",
    )

    assert tutor_mgr.record_learning_event(event_dup) is True
    mastery_after_first = tutor_mgr.get_student_concept_mastery("student_A", "chem_inorg_periodic")

    # Re-record duplicate event
    assert tutor_mgr.record_learning_event(event_dup) is False
    mastery_after_second = tutor_mgr.get_student_concept_mastery("student_A", "chem_inorg_periodic")

    assert mastery_after_first.mastery == mastery_after_second.mastery
    assert mastery_after_first.exposure_count == mastery_after_second.exposure_count


def test_uncertain_evaluation_does_not_mutate_mastery(tutor_mgr):
    '''P0-02 & P1-T03 Rule: 'uncertain' correctness does NOT alter student mastery.'''
    event_unc = LearningEvent(
        event_id="evt_uncertain_001",
        student_id="student_A",
        session_id="session_1",
        turn_id="turn_002",
        concept_id="chem_inorg_bonding",
        correctness="uncertain",
    )

    mastery_before = tutor_mgr.get_student_concept_mastery("student_A", "chem_inorg_bonding")
    assert tutor_mgr.record_learning_event(event_unc) is True
    mastery_after = tutor_mgr.get_student_concept_mastery("student_A", "chem_inorg_bonding")

    assert mastery_before.mastery == mastery_after.mastery
    assert mastery_after.exposure_count == 0


def test_session_does_not_reset_mastery(tutor_mgr):
    '''Verify creating a new session ID for the same student preserves mastery.'''
    event_s1 = LearningEvent(
        event_id="evt_session_1",
        student_id="student_persisted",
        session_id="session_1",
        turn_id="turn_01",
        concept_id="chem_thermo_gibbs",
        correctness="correct",
    )
    tutor_mgr.record_learning_event(event_s1)

    mastery_session_1 = tutor_mgr.get_student_concept_mastery("student_persisted", "chem_thermo_gibbs")
    assert mastery_session_1.mastery > 0.0

    # Simulate new session
    event_s2 = LearningEvent(
        event_id="evt_session_2",
        student_id="student_persisted",
        session_id="session_2",
        turn_id="turn_02",
        concept_id="chem_thermo_gibbs",
        correctness="correct",
    )
    tutor_mgr.record_learning_event(event_s2)

    mastery_session_2 = tutor_mgr.get_student_concept_mastery("student_persisted", "chem_thermo_gibbs")
    assert mastery_session_2.exposure_count == 2
    assert mastery_session_2.mastery > mastery_session_1.mastery


def test_hint_count_and_learning_status_persistence(tutor_mgr):
    '''Phase 1 Re-audit: Verify hint_count and learning_status persistence via migration 204.'''
    event_hint = LearningEvent(
        event_id="evt_hint_01",
        student_id="student_h1",
        session_id="sess_h1",
        turn_id="turn_h1",
        concept_id="thermo.enthalpy",
        correctness="correct",
        hint_used=1,
    )
    tutor_mgr.record_learning_event(event_hint)

    mastery = tutor_mgr.get_student_concept_mastery("student_h1", "thermo.enthalpy")
    assert mastery.hint_count == 1
    assert mastery.learning_status == "LEARNING"
