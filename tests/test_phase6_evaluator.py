"""Tests for Phase 6: Chemistry Answer Evaluator (Section 12).

Verifies that the evaluator:
1. Never allows ambiguous single words/numbers ('yes', 'correct', '400', '0') to prove arbitrary questions correct.
2. Evaluates numeric answers with tolerance.
3. Checks units for numeric responses and marks partial correctness for missing/wrong units.
4. Detects partial answers.
5. Identifies conceptual misconceptions and surfaces them in the result.
6. Gracefully handles unexpected evaluation pipeline exceptions as 'uncertain'.
7. Ensures 'uncertain' evaluation events never mutate student mastery state in TutorStateManager.
8. Complies with the Section 12 input/output schema.
"""
import pytest
from core.tutor.evaluator import StudentAnswerEvaluator, EvaluationResult
from core.tutor.state import TutorStateManager, LearningEvent


def test_yes_cannot_prove_arbitrary_question_correct():
    """Requirement: 'yes' cannot prove arbitrary question correct."""
    # 1. No context
    res_no_ctx = StudentAnswerEvaluator.evaluate(user_answer="yes")
    assert res_no_ctx.correctness != "correct"
    assert res_no_ctx.correctness == "uncertain"

    # 2. Conceptual question
    res_conceptual = StudentAnswerEvaluator.evaluate(
        user_answer="yes",
        question="Explain Hess's Law of constant heat summation.",
        expected_answer="Enthalpy change is independent of the pathway taken.",
        question_type="conceptual",
    )
    assert res_conceptual.correctness != "correct"

    # 3. Explanation question
    res_explanation = StudentAnswerEvaluator.evaluate_dict({
        "question_id": "q_thermo_01",
        "concept_id": "ncert_chem_11_thermo_hess",
        "question": "Why is enthalpy a state function?",
        "expected_answer": "Enthalpy depends only on the initial and final states of the system.",
        "student_answer": "yes",
        "question_type": "explanation",
    })
    assert res_explanation.correctness != "correct"


def test_correct_cannot_prove_arbitrary_question_correct():
    """Requirement: 'correct' cannot prove arbitrary question correct."""
    # 1. No context
    res_no_ctx = StudentAnswerEvaluator.evaluate(user_answer="correct")
    assert res_no_ctx.correctness != "correct"
    assert res_no_ctx.correctness == "uncertain"

    # 2. Formula question
    res_formula = StudentAnswerEvaluator.evaluate_dict({
        "question_id": "q_form_01",
        "concept_id": "ncert_chem_11_thermo_first_law",
        "question": "What is the mathematical formulation of the First Law of Thermodynamics?",
        "expected_answer": "delta U = q + w",
        "student_answer": "correct",
        "question_type": "formula",
    })
    assert res_formula.correctness != "correct"


def test_400_cannot_prove_arbitrary_question_correct():
    """Requirement: '400' cannot prove arbitrary question correct."""
    # 1. No context
    res_no_ctx = StudentAnswerEvaluator.evaluate(user_answer="400")
    assert res_no_ctx.correctness != "correct"
    assert res_no_ctx.correctness == "uncertain"

    # 2. Conceptual question
    res_conceptual = StudentAnswerEvaluator.evaluate(
        user_answer="400",
        question="Explain Gibbs free energy criterion for spontaneity.",
        expected_answer="Delta G must be negative for a spontaneous process at constant T and P.",
        question_type="conceptual",
    )
    assert res_conceptual.correctness != "correct"

    # 3. Numeric question where 400 is WRONG
    res_numeric_wrong = StudentAnswerEvaluator.evaluate(
        user_answer="400",
        question="Calculate standard enthalpy of reaction",
        expected_answer="-285.8 kJ/mol",
        question_type="numeric",
    )
    assert res_numeric_wrong.correctness == "incorrect"
    assert res_numeric_wrong.error_type == "arithmetic"


def test_0_cannot_prove_arbitrary_question_correct():
    """Requirement: '0' cannot prove arbitrary question correct."""
    # 1. No context
    res_no_ctx = StudentAnswerEvaluator.evaluate(user_answer="0")
    assert res_no_ctx.correctness != "correct"
    assert res_no_ctx.correctness == "uncertain"

    # 2. Conceptual question
    res_conceptual = StudentAnswerEvaluator.evaluate(
        user_answer="0",
        question="What is the third law of thermodynamics?",
        expected_answer="The entropy of a perfectly crystalline substance approaches zero as temperature approaches absolute zero.",
        question_type="conceptual",
    )
    assert res_conceptual.correctness != "correct"

    # 3. Numeric question where 0 is WRONG
    res_numeric_wrong = StudentAnswerEvaluator.evaluate(
        user_answer="0",
        question="Calculate delta H",
        expected_answer="150 kJ",
        question_type="numeric",
    )
    assert res_numeric_wrong.correctness == "incorrect"


def test_numeric_tolerance_works():
    """Requirement: numeric tolerance works."""
    # Expected: 100.0, tolerance 5% (0.05). Range: [95.0, 105.0]
    res_exact = StudentAnswerEvaluator.evaluate(
        user_answer="100.0",
        expected_answer="100.0",
        question_type="numeric",
        tolerance=0.05,
    )
    assert res_exact.correctness == "correct"
    assert res_exact.error_type == "none"

    res_within_tol = StudentAnswerEvaluator.evaluate(
        user_answer="103.5",
        expected_answer="100.0",
        question_type="numeric",
        tolerance=0.05,
    )
    assert res_within_tol.correctness == "correct"
    assert res_within_tol.error_type == "none"

    res_outside_tol = StudentAnswerEvaluator.evaluate(
        user_answer="112.0",
        expected_answer="100.0",
        question_type="numeric",
        tolerance=0.05,
    )
    assert res_outside_tol.correctness == "incorrect"
    assert res_outside_tol.error_type == "arithmetic"


def test_units_are_checked():
    """Requirement: units are checked."""
    # 1. Correct value AND correct unit
    res_with_unit = StudentAnswerEvaluator.evaluate(
        user_answer="-285.8 kJ/mol",
        expected_answer="-285.8 kJ/mol",
        expected_unit="kJ/mol",
        question_type="numeric",
    )
    assert res_with_unit.correctness == "correct"
    assert res_with_unit.error_type == "none"

    # 2. Correct value BUT missing unit -> partially_correct with unit error
    res_missing_unit = StudentAnswerEvaluator.evaluate(
        user_answer="-285.8",
        expected_answer="-285.8 kJ/mol",
        expected_unit="kJ/mol",
        question_type="numeric",
    )
    assert res_missing_unit.correctness == "partially_correct"
    assert res_missing_unit.error_type == "unit"
    assert res_missing_unit.recommended_action == "reinforce"


def test_partial_answers_are_detected():
    """Requirement: partial answers are detected."""
    # Short answer / conceptual with partial keyword coverage
    res = StudentAnswerEvaluator.evaluate(
        user_answer="It involves enthalpy and state function.",
        expected_answer="Hess's law states that the total enthalpy change for a chemical reaction is independent of the pathway or number of steps taken because enthalpy is a state function.",
        rubric="Mention total enthalpy change, independence of pathway, and state function property.",
        question_type="short_answer",
    )
    assert res.correctness == "partially_correct"
    assert res.error_type == "conceptual"
    assert res.recommended_action == "reinforce"


def test_conceptual_misconceptions_are_detected():
    """Requirement: conceptual misconceptions are detected."""
    res = StudentAnswerEvaluator.evaluate_dict({
        "question_id": "q_hess_02",
        "concept_id": "ncert_chem_11_thermo_hess",
        "question": "What happens to delta H when a reaction equation is inverted?",
        "expected_answer": "The sign of delta H is reversed.",
        "student_answer": "When you invert or change direction the hess reaction enthalpy stays same",
        "question_type": "conceptual",
    })
    assert res.correctness == "incorrect"
    assert res.error_type == "conceptual"
    assert res.misconception == "HESS_LAW_DIRECTION"
    assert res.recommended_action == "remediate"


def test_evaluation_failure_becomes_uncertain(monkeypatch):
    """Requirement: evaluation failure becomes uncertain."""
    # Force an unexpected internal error during evaluation
    def crashing_search(*args, **kwargs):
        raise RuntimeError("Simulated evaluator engine breakdown")

    monkeypatch.setattr("core.tutor.evaluator.re.search", crashing_search)

    res = StudentAnswerEvaluator.evaluate(
        user_answer="100 kJ",
        expected_answer="100 kJ",
        question_type="numeric",
    )
    assert res.correctness == "uncertain"
    assert res.confidence == 0.0
    assert res.error_type == "other"
    assert "Evaluation pipeline exception" in res.evidence[0]


def test_uncertain_does_not_change_mastery(tmp_path):
    """Requirement: 'uncertain' must not change mastery."""
    db_path = str(tmp_path / "test_eval_uncertain.db")
    sm = TutorStateManager(db_path)

    # Initial mastery
    initial_mastery = sm.get_student_concept_mastery("student_u1", "concept_u1")
    assert initial_mastery.mastery == 0.0
    assert initial_mastery.exposure_count == 0
    assert initial_mastery.correct_count == 0
    assert initial_mastery.error_count == 0

    # Record 'uncertain' event
    uncertain_event = LearningEvent(
        event_id="evt_unc_01",
        student_id="student_u1",
        session_id="sess_u1",
        turn_id="turn_u1",
        concept_id="concept_u1",
        correctness="uncertain",
        confidence=0.0,
    )
    sm.record_learning_event(uncertain_event)

    # Post-record check: mastery and counts must NOT have changed
    post_mastery = sm.get_student_concept_mastery("student_u1", "concept_u1")
    assert post_mastery.mastery == 0.0
    assert post_mastery.exposure_count == 0
    assert post_mastery.correct_count == 0
    assert post_mastery.error_count == 0


def test_section_12_schema_contract():
    """Verify to_dict() outputs all required Section 12 keys."""
    res = StudentAnswerEvaluator.evaluate_dict({
        "question_id": "q_chem_01",
        "concept_id": "ncert_chem_11_thermo_first_law",
        "question": "State first law of thermodynamics",
        "expected_answer": "Energy can neither be created nor destroyed",
        "student_answer": "Energy cannot be created or destroyed",
        "question_type": "explanation",
    })
    d = res.to_dict()

    assert "correctness" in d
    assert d["correctness"] in ("correct", "partially_correct", "incorrect", "uncertain")
    assert "confidence" in d
    assert isinstance(d["confidence"], float)
    assert "error_type" in d
    assert d["error_type"] in ("none", "conceptual", "arithmetic", "formula", "unit", "reaction", "notation", "other")
    assert "misconception" in d
    assert "recommended_action" in d
    assert d["recommended_action"] in ("advance", "reinforce", "remediate", "prerequisite_review")
