"""Phase 6 Test Suite: Assessment Engine.

Verifies question bank schema, session persistence, attempt recording,
grading, score calculation, and student learning state updates (P6-T01 through P6-T04).
"""
import pytest
import tempfile
from pathlib import Path

from core.assessment.manager import AssessmentManager, QuestionBankItem
from core.tutor.state import TutorStateManager


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


def test_assessment_session_lifecycle(temp_state_manager):
    mgr = AssessmentManager(state_manager=temp_state_manager)

    # 1. Create session
    assessment_id = mgr.create_assessment_session(
        student_id="student_assess_1",
        concepts=["thermo.hess_law", "thermo.gibbs"],
        question_count=2,
    )
    assert assessment_id.startswith("assess_")

    # 2. Submit attempts
    res1 = mgr.submit_attempt(
        assessment_id=assessment_id,
        student_id="student_assess_1",
        question_id="thermo.hess.001",
        student_answer="-110.5",
    )
    assert res1["is_correct"] is True
    assert res1["score_fraction"] == 1.0

    res2 = mgr.submit_attempt(
        assessment_id=assessment_id,
        student_id="student_assess_1",
        question_id="thermo.gibbs.001",
        student_answer="delta G > 0",  # Incorrect
    )
    assert res2["is_correct"] is False
    assert res2["score_fraction"] == 0.0

    # 3. Complete session & verify score computation
    final_res = mgr.complete_assessment_session(assessment_id=assessment_id, student_id="student_assess_1")
    assert final_res["status"] == "COMPLETED"
    assert final_res["score_percentage"] == 50.0
    assert "thermo.hess_law" in final_res["strengths"]
    assert "thermo.gibbs" in final_res["weaknesses"]

    # 4. Verify student concept mastery updated from assessment events
    mastery_hess = temp_state_manager.get_student_concept_mastery("student_assess_1", "thermo.hess_law")
    assert mastery_hess.exposure_count >= 1
    assert mastery_hess.correct_count >= 1
