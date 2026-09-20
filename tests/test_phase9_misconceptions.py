"""Tests for Phase 9: Misconception Tracking (Section 15).

Verifies:
1. Catalog completeness:
   - 7 Thermodynamics codes:
     THERMO_SIGN_CONVENTION, HEAT_VS_INTERNAL_ENERGY, STATE_VS_PATH_FUNCTION,
     ENTHALPY_CONFUSION, HESS_LAW_DIRECTION, CP_CV_CONFUSION, GIBBS_SIGN_CONFUSION
   - 8 Inorganic Chemistry codes:
     PERIODIC_TREND_CONFUSION, OXIDATION_STATE_ERROR, ELECTRONIC_CONFIGURATION_ERROR,
     COORDINATION_NUMBER_CONFUSION, LIGAND_CONFUSION, REDOX_CONFUSION,
     ANOMALOUS_BEHAVIOUR_CONFUSION, METALLURGY_PROCESS_CONFUSION
2. Accurate classification across all cataloged patterns.
3. The required lifecycle loop:
   wrong answer → classify error → persist misconception → remediation → retest → resolution.
"""
import pytest

from core.learning.misconceptions import (
    THERMODYNAMICS_MISCONCEPTIONS,
    INORGANIC_MISCONCEPTIONS,
    ALL_MISCONCEPTIONS,
    MisconceptionTracker,
    StudentMisconceptionRecord,
    get_remediation_guidance,
)
from core.tutor.state import TutorStateManager, LearningEvent
from core.tutor.evaluator import StudentAnswerEvaluator


def test_misconception_catalog_completeness():
    """Section 15: Verify all 7 Thermodynamics and 8 Inorganic misconception codes are registered."""
    expected_thermo = {
        'THERMO_SIGN_CONVENTION',
        'HEAT_VS_INTERNAL_ENERGY',
        'STATE_VS_PATH_FUNCTION',
        'ENTHALPY_CONFUSION',
        'HESS_LAW_DIRECTION',
        'CP_CV_CONFUSION',
        'GIBBS_SIGN_CONFUSION',
    }
    expected_inorg = {
        'PERIODIC_TREND_CONFUSION',
        'OXIDATION_STATE_ERROR',
        'ELECTRONIC_CONFIGURATION_ERROR',
        'COORDINATION_NUMBER_CONFUSION',
        'LIGAND_CONFUSION',
        'REDOX_CONFUSION',
        'ANOMALOUS_BEHAVIOUR_CONFUSION',
        'METALLURGY_PROCESS_CONFUSION',
    }

    assert expected_thermo.issubset(set(THERMODYNAMICS_MISCONCEPTIONS.keys()))
    assert expected_inorg.issubset(set(INORGANIC_MISCONCEPTIONS.keys()))
    assert (expected_thermo | expected_inorg).issubset(set(ALL_MISCONCEPTIONS.keys()))


def test_thermodynamics_misconceptions_classification():
    """Verify classification of Thermodynamics misconception patterns."""
    tracker = MisconceptionTracker

    # 1. THERMO_SIGN_CONVENTION
    assert tracker.identify_misconception_from_error(
        "chem_thermo_first_law", "work done by the system is +w", error_type="sign error"
    ) == 'THERMO_SIGN_CONVENTION'

    # 2. HEAT_VS_INTERNAL_ENERGY
    assert tracker.identify_misconception_from_error(
        "chem_thermo_first_law", "heat and internal energy are the same thing q vs u"
    ) == 'HEAT_VS_INTERNAL_ENERGY'

    # 3. STATE_VS_PATH_FUNCTION
    assert tracker.identify_misconception_from_error(
        "chem_thermo_system", "work is a state function independent of path"
    ) == 'STATE_VS_PATH_FUNCTION'

    # 4. ENTHALPY_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_thermo_enthalpy", "enthalpy is just h vs u internal energy"
    ) == 'ENTHALPY_CONFUSION'

    # 5. HESS_LAW_DIRECTION
    assert tracker.identify_misconception_from_error(
        "chem_thermo_hess", "when you invert the hess equation direction enthalpy stays same"
    ) == 'HESS_LAW_DIRECTION'

    # 6. CP_CV_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_thermo_heat_cap", "cp and cv are identical for all gases"
    ) == 'CP_CV_CONFUSION'

    # 7. GIBBS_SIGN_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_thermo_gibbs", "reaction is spontaneous when delta g is positive"
    ) == 'GIBBS_SIGN_CONFUSION'


def test_inorganic_misconceptions_classification():
    """Verify classification of Inorganic Chemistry misconception patterns."""
    tracker = MisconceptionTracker

    # 1. PERIODIC_TREND_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_inorg_periodic", "ionization enthalpy decreases across a period due to radius"
    ) == 'PERIODIC_TREND_CONFUSION'

    # 2. OXIDATION_STATE_ERROR
    assert tracker.identify_misconception_from_error(
        "chem_inorg_bonding", "the oxidation number of Mn in KMnO4 is +5"
    ) == 'OXIDATION_STATE_ERROR'

    # 3. ELECTRONIC_CONFIGURATION_ERROR
    assert tracker.identify_misconception_from_error(
        "chem_inorg_electronic", "Chromium aufbau electronic configuration has 4s2 3d4"
    ) == 'ELECTRONIC_CONFIGURATION_ERROR'

    # 4. COORDINATION_NUMBER_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_inorg_bonding", "coordination number is equal to oxidation state"
    ) == 'COORDINATION_NUMBER_CONFUSION'

    # 5. LIGAND_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_inorg_bonding", "oxalate is a monodentate ligand"
    ) == 'LIGAND_CONFUSION'

    # 6. REDOX_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_inorg_bonding", "an oxidizing agent loses electrons and gets oxidized"
    ) == 'REDOX_CONFUSION'

    # 7. ANOMALOUS_BEHAVIOUR_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_inorg_pblock", "nitrogen forms pentahalides just like phosphorus, no anomalous behavior"
    ) == 'ANOMALOUS_BEHAVIOUR_CONFUSION'

    # 8. METALLURGY_PROCESS_CONFUSION
    assert tracker.identify_misconception_from_error(
        "chem_inorg_sblock", "calcination is roasting in excess air for sulfides in metallurgy"
    ) == 'METALLURGY_PROCESS_CONFUSION'


def test_remediation_guidance_available_for_all_codes():
    """Verify every registered misconception code provides clear remediation guidance."""
    for code in ALL_MISCONCEPTIONS:
        guidance = get_remediation_guidance(code)
        assert guidance != ""
        assert len(guidance) >= 20, f"Remediation guidance too short for {code}"


def test_required_lifecycle_loop(tmp_path):
    """Section 15: Verify complete lifecycle loop:
    wrong answer → classify error → persist misconception → remediation → retest → resolution.
    """
    db_path = str(tmp_path / "test_misconception_loop.db")
    sm = TutorStateManager(db_path)
    tracker = MisconceptionTracker(sm)

    student_id = "student_loop_01"
    concept_id = "chem_thermo_hess"

    # Step 1: Wrong answer submitted by student
    student_wrong_answer = "When you invert the reaction equation, delta H stays positive."

    # Step 2: Classify error and identify misconception
    eval_result = StudentAnswerEvaluator.evaluate_dict({
        "question_id": "q_hess_01",
        "concept_id": concept_id,
        "question": "What happens to delta H when you invert a thermochemical equation?",
        "expected_answer": "The sign of delta H is reversed.",
        "student_answer": student_wrong_answer,
        "question_type": "conceptual",
    })
    assert eval_result.correctness == "incorrect"
    assert eval_result.error_type == "conceptual"
    assert eval_result.misconception == "HESS_LAW_DIRECTION"

    # Step 3: Persist misconception
    record = tracker.record_misconception(student_id, concept_id, eval_result.misconception)
    assert record.misconception_code == "HESS_LAW_DIRECTION"
    assert record.occurrence_count == 1
    assert record.resolved is False

    # Check active misconceptions
    active_before = tracker.get_active_misconceptions(student_id, concept_id)
    assert len(active_before) == 1
    assert active_before[0].misconception_code == "HESS_LAW_DIRECTION"

    # Step 4: Remediation guidance is retrieved
    remediation = get_remediation_guidance(eval_result.misconception)
    assert "reversing" in remediation.lower()
    assert "sign" in remediation.lower()

    # Step 5: Retest — student answers correctly after remediation
    student_correct_answer = "The sign of delta H is reversed to negative 50 kJ."
    retest_result = StudentAnswerEvaluator.evaluate_dict({
        "question_id": "q_hess_02",
        "concept_id": concept_id,
        "question": "If reaction A -> B has delta H = +50 kJ, what is delta H for B -> A?",
        "expected_answer": "The sign of delta H is reversed to negative 50 kJ",
        "rubric": "Reversed sign to negative 50 kJ",
        "student_answer": student_correct_answer,
        "question_type": "conceptual",
    })
    assert retest_result.correctness == "correct"
    assert retest_result.error_type == "none"

    # Step 6: Resolution
    tracker.resolve_misconception(student_id, concept_id, eval_result.misconception)
    active_after = tracker.get_active_misconceptions(student_id, concept_id)
    assert len(active_after) == 0, "Resolved misconception should no longer appear in active misconceptions"
