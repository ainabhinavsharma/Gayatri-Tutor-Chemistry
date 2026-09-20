"""Tests for Phase 4: Student Data Isolation (P0).

Verifies:
1. Strict segregation of global curriculum from student learning state.
2. StudentConceptMastery schema contains all 12 required fields.
3. Student A cannot read Student B's state (SecurityAccessDeniedError).
4. Student A cannot modify Student B's state.
5. Student A's learning events do not mutate or influence Student B's mastery.
6. Session reset clears conversation context without deleting student mastery.
7. Client-supplied student ID spoofing is rejected.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from dataclasses import fields

from core.tutor.state import TutorStateManager, StudentConceptMastery, LearningEvent
from core.curriculum.loader import CurriculumManifestLoader
from core.security.authorization import StudentAuthorizationGuard, SecurityAccessDeniedError
from core.orchestrator import Orchestrator, TurnOptions


def test_student_concept_mastery_schema_12_fields():
    """Verify StudentConceptMastery has all 12 required fields."""
    expected_fields = {
        "student_id",
        "concept_id",
        "mastery",
        "confidence",
        "exposure_count",
        "correct_count",
        "error_count",
        "hint_count",
        "last_practiced",
        "next_review_at",
        "difficulty_level",
        "learning_status",
    }
    actual_fields = {f.name for f in fields(StudentConceptMastery)}
    assert expected_fields.issubset(actual_fields), f"Missing fields: {expected_fields - actual_fields}"


def test_curriculum_isolated_from_student_state():
    """Verify global curriculum contains no student state and is read-only."""
    loader = CurriculumManifestLoader()
    manifest = loader.load_manifest()

    assert len(manifest.domains) > 0
    for domain in manifest.domains:
        # Curriculum domains must not contain student identifiers or state
        assert not hasattr(domain, "student_id")
        assert not hasattr(domain, "mastery")
        assert not hasattr(domain, "correct_count")


def test_student_cross_read_blocked():
    """Verify Student A cannot read Student B's data via authorization guard."""
    student_a = "student_alpha"
    student_b = "student_beta"

    # Authorized: Student A accessing Student A
    StudentAuthorizationGuard.validate_student_access(student_a, student_a)

    # Unauthorized: Student A accessing Student B
    with pytest.raises(SecurityAccessDeniedError) as exc_info:
        StudentAuthorizationGuard.validate_student_access(student_a, student_b)
    assert "Cross-student access blocked" in str(exc_info.value)


def test_student_cross_modify_and_influence_isolated(tmp_path):
    """Verify Student A cannot modify Student B and Student A's mastery cannot affect Student B."""
    db_file = tmp_path / "test_isolation.db"
    manager = TutorStateManager(db_path=db_file)

    student_a = "student_alpha"
    student_b = "student_beta"
    concept = "chem_thermo_first_law"

    # Initial state: both have default 0.0 mastery
    mastery_a_init = manager.get_student_concept_mastery(student_a, concept)
    mastery_b_init = manager.get_student_concept_mastery(student_b, concept)
    assert mastery_a_init.mastery == 0.0
    assert mastery_b_init.mastery == 0.0

    # Student A completes 3 successful learning events
    for i in range(3):
        ev_a = LearningEvent(
            event_id=f"ev_a_{i}",
            student_id=student_a,
            session_id="sess_a",
            turn_id=f"t_a_{i}",
            concept_id=concept,
            correctness="correct",
            difficulty=0.5
        )
        manager.record_learning_event(ev_a)

    # Re-fetch both states
    mastery_a = manager.get_student_concept_mastery(student_a, concept)
    mastery_b = manager.get_student_concept_mastery(student_b, concept)

    # Student A's mastery must have increased
    assert mastery_a.mastery > 0.0
    assert mastery_a.correct_count == 3
    assert mastery_a.exposure_count == 3

    # Student B's mastery MUST REMAIN COMPLETELY UNCHANGED
    assert mastery_b.mastery == 0.0
    assert mastery_b.correct_count == 0
    assert mastery_b.exposure_count == 0
    assert mastery_b.error_count == 0


def test_session_reset_preserves_student_mastery(tmp_path):
    """Verify session reset does not accidentally delete student-wide mastery."""
    db_file = tmp_path / "test_session_reset.db"
    manager = TutorStateManager(db_path=db_file)

    student_id = "student_gamma"
    concept = "chem_thermo_entropy"

    # Record progress for student
    ev = LearningEvent(
        event_id="ev_gamma_1",
        student_id=student_id,
        session_id="sess_gamma",
        turn_id="t_1",
        concept_id=concept,
        correctness="correct",
        difficulty=0.6
    )
    manager.record_learning_event(ev)

    mastery_before = manager.get_student_concept_mastery(student_id, concept)
    assert mastery_before.mastery > 0.0

    # Execute session clear on orchestrator
    orchestrator = Orchestrator()
    orchestrator.clear_session("sess_gamma")

    # Verify student mastery is preserved
    mastery_after = manager.get_student_concept_mastery(student_id, concept)
    assert mastery_after.mastery == mastery_before.mastery
    assert mastery_after.correct_count == mastery_before.correct_count
    assert mastery_after.exposure_count == mastery_before.exposure_count


def test_client_supplied_student_id_rejected():
    """Verify that unverified or mismatched student IDs are rejected."""
    # Blank or empty student ID
    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("", "student_target")

    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("student_requester", "")

    # Whitespace-only spoof
    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("   ", "student_target")
