"""Tests for Phase 7: Assessment Engine (P6-T01 to P6-T04)."""
import pytest
from core.tutor.state import TutorStateManager
from core.assessment.schema import MCQQuestion, NumericalQuestion, AssertionReasoningQuestion, EquationBalancingQuestion
from core.assessment.grader import AssessmentGrader
from core.assessment.manager import AssessmentManager, SAMPLE_QUESTION_BANK


def test_anti_leakage_sanitizer():
    """Test that sanitize_for_client strips correct_answer, explanation, and answer keys."""
    q = MCQQuestion(
        question_id="mcq.test.01",
        topic_id="thermo.hess",
        difficulty=2,
        question_text="What is Hess Law?",
        correct_answer="Enthalpy change is independent of path",
        explanation="State function property",
    )
    sanitized = AssessmentGrader.sanitize_for_client(q)
    assert "correct_answer" not in sanitized
    assert "explanation" not in sanitized
    assert "correct_index" not in sanitized
    assert sanitized["question"] == "What is Hess Law?"


def test_grade_mcq_correct_and_incorrect():
    """Test MCQ grading accuracy."""
    q = MCQQuestion(
        question_id="mcq.02",
        topic_id="thermo.gibbs",
        difficulty=2,
        question_text="Condition for spontaneity?",
        correct_answer="delta G < 0",
        explanation="Gibbs free energy definition",
    )
    is_corr, score, fb = AssessmentGrader.grade_answer(q, "delta G < 0")
    assert is_corr is True
    assert score == 1.0

    is_corr, score, fb = AssessmentGrader.grade_answer(q, "delta G > 0")
    assert is_corr is False
    assert score == 0.0


def test_grade_numerical_within_tolerance():
    """Test numerical grading with tolerance."""
    q = NumericalQuestion(
        question_id="num.01",
        topic_id="thermo.hess",
        difficulty=3,
        question_text="Calculate delta H",
        expected_value=-110.5,
        tolerance=0.05,
    )
    # Exact answer
    is_corr, score, fb = AssessmentGrader.grade_answer(q, "-110.5")
    assert is_corr is True
    assert score == 1.0

    # Within tolerance (-110.5 * 0.05 = ~5.5)
    is_corr, score, fb = AssessmentGrader.grade_answer(q, "-112.0")
    assert is_corr is True

    # Outside tolerance
    is_corr, score, fb = AssessmentGrader.grade_answer(q, "-150.0")
    assert is_corr is False


def test_grade_equation_balancing():
    """Test equation balancing engine integration in grader."""
    q = EquationBalancingQuestion(
        question_id="eq.01",
        topic_id="inorganic.redox",
        difficulty=2,
        question_text="Balance H2 + O2 -> H2O",
        unbalanced_equation="H2 + O2 -> H2O",
        balanced_equation="2 H2 + O2 -> 2 H2O",
    )
    is_corr, score, fb = AssessmentGrader.grade_answer(q, "2 H2 + O2 -> 2 H2O")
    assert is_corr is True
    assert score == 1.0

    is_corr, score, fb = AssessmentGrader.grade_answer(q, "H2 + O2 -> H2O")
    assert is_corr is False


def test_assessment_manager_session_lifecycle(tmp_path):
    """Test create session, submit attempts, complete session, and verify learner state updates."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    mgr = AssessmentManager(state_manager=sm, questions=SAMPLE_QUESTION_BANK)

    # 1. Create Session
    assess_id = mgr.create_assessment_session(
        student_id="student_assess_1",
        concepts=["thermo.hess_law", "thermo.gibbs"],
        question_count=2,
    )
    assert assess_id.startswith("assess_")

    # 2. Submit Attempt 1 (Correct)
    att1 = mgr.submit_attempt(
        assessment_id=assess_id,
        student_id="student_assess_1",
        question_id="thermo.hess.001",
        student_answer="-110.5",
    )
    assert att1["is_correct"] is True
    assert att1["score_fraction"] == 1.0

    # 3. Submit Attempt 2 (Incorrect - triggers misconception tracking)
    att2 = mgr.submit_attempt(
        assessment_id=assess_id,
        student_id="student_assess_1",
        question_id="thermo.gibbs.001",
        student_answer="delta G > 0",
    )
    assert att2["is_correct"] is False
    assert att2["detected_misconception"] == "GIBBS_SIGN_CONFUSION"

    # 4. Complete Session
    summary = mgr.complete_assessment_session(assess_id, "student_assess_1")
    assert summary["status"] == "COMPLETED"
    assert summary["score_percentage"] == 50.0
    assert summary["total_attempts"] == 2
    assert "thermo.hess_law" in summary["strengths"]
    assert "thermo.gibbs" in summary["weaknesses"]

    # 5. Verify Learner State Mutation in Database
    mastery_hess = sm.get_student_concept_mastery("student_assess_1", "thermo.hess_law")
    assert mastery_hess.exposure_count >= 1
    assert mastery_hess.correct_count >= 1

    mastery_gibbs = sm.get_student_concept_mastery("student_assess_1", "thermo.gibbs")
    assert mastery_gibbs.exposure_count >= 1
    assert mastery_gibbs.error_count >= 1
