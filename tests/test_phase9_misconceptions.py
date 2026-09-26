"""Phase 9 Test Suite — Chemistry Misconception Intelligence (Section 15 & Section 23)."""
import pytest
from core.tutor.state import TutorStateManager
from core.learning.misconceptions import (
    MisconceptionTracker,
    ALL_MISCONCEPTIONS,
    THERMODYNAMICS_MISCONCEPTIONS,
    INORGANIC_MISCONCEPTIONS,
    BONDING_MISCONCEPTIONS,
    EQUILIBRIUM_MISCONCEPTIONS,
    REMEDIATION_GUIDANCE,
    get_remediation_guidance,
)


def test_misconception_catalog_completeness():
    """Verify that all major chemistry domains are present in ALL_MISCONCEPTIONS."""
    assert len(THERMODYNAMICS_MISCONCEPTIONS) >= 7
    assert len(INORGANIC_MISCONCEPTIONS) >= 8
    assert len(BONDING_MISCONCEPTIONS) >= 3
    assert len(EQUILIBRIUM_MISCONCEPTIONS) >= 3
    assert len(ALL_MISCONCEPTIONS) == (
        len(THERMODYNAMICS_MISCONCEPTIONS)
        + len(INORGANIC_MISCONCEPTIONS)
        + len(BONDING_MISCONCEPTIONS)
        + len(EQUILIBRIUM_MISCONCEPTIONS)
    )


def test_thermodynamics_misconceptions_classification():
    """Verify classification of Thermodynamics misconceptions."""
    code_sign = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_thermo_first_law",
        student_answer="500 + 200 = 700 J",
    )
    assert code_sign == "THERMO_SIGN_CONVENTION"

    code_hess = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_thermo_hess_law",
        student_answer="Inverted reaction keeping same enthalpy sign",
    )
    assert code_hess == "HESS_LAW_DIRECTION"

    code_gibbs = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_thermo_gibbs",
        student_answer="Delta G is positive for spontaneous reaction",
    )
    assert code_gibbs == "GIBBS_SIGN_CONFUSION"


def test_inorganic_misconceptions_classification():
    """Verify classification of Inorganic Chemistry misconceptions."""
    code_trend = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_inorg_periodic",
        student_answer="Atomic radius increases across period",
    )
    assert code_trend == "PERIODIC_TREND_CONFUSION"

    code_ox = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_inorg_pblock",
        student_answer="Wrong oxidation state for central atom",
    )
    assert code_ox == "OXIDATION_STATE_ERROR"

    code_vsepr = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_inorg_bonding",
        student_answer="VSEPR electron geometry vs molecular shape confusion",
    )
    assert code_vsepr == "VSEPR_GEOMETRY_CONFUSION"

    code_cat = MisconceptionTracker.identify_misconception_from_error(
        concept_id="chem_equil_le_chatelier",
        student_answer="Adding catalyst shifts equilibrium to product side",
    )
    assert code_cat == "LE_CHATELIER_CATALYST_CONFUSION"


def test_remediation_guidance_available_for_all_codes():
    """Verify that every misconception code in ALL_MISCONCEPTIONS has a corresponding remediation directive."""
    for code in ALL_MISCONCEPTIONS:
        guidance = get_remediation_guidance(code)
        assert guidance is not None
        assert len(guidance) > 15
        assert code in REMEDIATION_GUIDANCE or "Review core curriculum principles" not in guidance


def test_required_lifecycle_loop(tmp_path):
    """Verify the full lifecycle: detect -> record -> query -> remediate -> resolve."""
    db_path = str(tmp_path / "test_lifecycle.db")
    sm = TutorStateManager(db_path=db_path)
    tracker = MisconceptionTracker(state_manager=sm)

    student_id = "student_ph9"
    concept_id = "chem_thermo_first_law"
    error_answer = "Work of expansion is +200 J"

    # 1. Detect
    code = tracker.identify_misconception_from_error(concept_id, error_answer)
    assert code == "THERMO_SIGN_CONVENTION"

    # 2. Record
    rec = tracker.record_misconception(student_id, concept_id, code)
    assert rec.occurrence_count == 1
    assert rec.resolved is False

    # 3. Query active
    active = tracker.get_active_misconceptions(student_id)
    assert len(active) == 1
    assert active[0].misconception_code == "THERMO_SIGN_CONVENTION"

    # 4. Remediation directive fetch
    guidance = get_remediation_guidance(code)
    assert "IUPAC" in guidance or "work" in guidance.lower()

    # 5. Resolve
    tracker.resolve_misconception(student_id, concept_id, code)
    active_after = tracker.get_active_misconceptions(student_id)
    assert len(active_after) == 0
