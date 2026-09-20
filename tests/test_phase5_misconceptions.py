"""Tests for Phase 5: Misconception Engine (P4-T03)."""
import pytest
from core.tutor.state import TutorStateManager
from core.learning.misconceptions import (
    MisconceptionTracker,
    ALL_MISCONCEPTIONS,
    THERMODYNAMICS_MISCONCEPTIONS,
    INORGANIC_MISCONCEPTIONS,
)


def test_identify_misconception_thermo():
    """Test identifying thermodynamics misconceptions from errors and student answers."""
    code1 = MisconceptionTracker.identify_misconception_from_error(
        concept_id="thermo.hess_law",
        student_answer="Inverted reaction without reversing enthalpy sign",
    )
    assert code1 == "HESS_LAW_DIRECTION"

    code2 = MisconceptionTracker.identify_misconception_from_error(
        concept_id="thermo.gibbs",
        student_answer="Delta G > 0 is spontaneous",
    )
    assert code2 == "GIBBS_SIGN_CONFUSION"

    code3 = MisconceptionTracker.identify_misconception_from_error(
        concept_id="thermo.work",
        student_answer="Confused sign convention for +w vs -w",
    )
    assert code3 == "THERMO_SIGN_CONVENTION"


def test_identify_misconception_inorganic():
    """Test identifying inorganic chemistry misconceptions from errors and student answers."""
    code1 = MisconceptionTracker.identify_misconception_from_error(
        concept_id="inorganic.periodic_trends",
        student_answer="Predicted atomic radius increases across a period",
    )
    assert code1 == "PERIODIC_TREND_CONFUSION"

    code2 = MisconceptionTracker.identify_misconception_from_error(
        concept_id="inorganic.transition_elements",
        student_answer="Wrong oxidation state calculation for KMnO4",
    )
    assert code2 == "OXIDATION_STATE_ERROR"

    code3 = MisconceptionTracker.identify_misconception_from_error(
        concept_id="inorganic.electronic_config",
        student_answer="Chromium electronic configuration aufbau exception error",
    )
    assert code3 == "ELECTRONIC_CONFIGURATION_ERROR"


def test_identify_explicit_error_code():
    """Test passing explicit error type directly."""
    code = MisconceptionTracker.identify_misconception_from_error(
        concept_id="any.concept",
        student_answer="Some answer",
        error_type="LIGAND_CONFUSION",
    )
    assert code == "LIGAND_CONFUSION"


def test_record_and_get_misconception(tmp_path):
    """Test recording and querying active misconceptions for a student."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    tracker = MisconceptionTracker(state_manager=sm)

    record1 = tracker.record_misconception(
        student_id="student_101",
        concept_id="thermo.hess",
        misconception_code="HESS_LAW_DIRECTION",
    )
    assert record1.occurrence_count == 1
    assert record1.resolved is False

    # Increment count
    record2 = tracker.record_misconception(
        student_id="student_101",
        concept_id="thermo.hess",
        misconception_code="HESS_LAW_DIRECTION",
    )
    assert record2.occurrence_count == 2

    # Query active
    active = tracker.get_active_misconceptions("student_101")
    assert len(active) == 1
    assert active[0].misconception_code == "HESS_LAW_DIRECTION"
    assert active[0].occurrence_count == 2


def test_resolve_misconception(tmp_path):
    """Test marking a misconception as resolved."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    tracker = MisconceptionTracker(state_manager=sm)

    tracker.record_misconception(
        student_id="student_202",
        concept_id="inorganic.periodic",
        misconception_code="PERIODIC_TREND_CONFUSION",
    )
    assert len(tracker.get_active_misconceptions("student_202")) == 1

    tracker.resolve_misconception(
        student_id="student_202",
        concept_id="inorganic.periodic",
        misconception_code="PERIODIC_TREND_CONFUSION",
    )
    assert len(tracker.get_active_misconceptions("student_202")) == 0


def test_student_isolation(tmp_path):
    """Test student isolation in misconception tracking."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    tracker = MisconceptionTracker(state_manager=sm)

    tracker.record_misconception("student_A", "concept_1", "THERMO_SIGN_CONVENTION")
    tracker.record_misconception("student_B", "concept_1", "GIBBS_SIGN_CONFUSION")

    active_A = tracker.get_active_misconceptions("student_A")
    active_B = tracker.get_active_misconceptions("student_B")

    assert len(active_A) == 1
    assert active_A[0].misconception_code == "THERMO_SIGN_CONVENTION"
    assert len(active_B) == 1
    assert active_B[0].misconception_code == "GIBBS_SIGN_CONFUSION"
