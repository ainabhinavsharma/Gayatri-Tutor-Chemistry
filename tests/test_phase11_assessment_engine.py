"""Phase 11: Assessment Engine Tests (Section 17).

Verifies:
1. Question schema supports all 11 required fields:
   (id, concept_id, difficulty, type, question, answer, rubric, hint, explanation, common_misconceptions, source)
   across all question types and serialized via to_dict().
2. Persistence across all 4 required tables:
   assessment, assessment_question, assessment_attempt, score.
3. Assessment outcomes reliably convert to LearningEvents and update student mastery without data loss.
4. Grader client sanitization strips answers and explanations.
"""
import json
import pytest
from core.tutor.state import TutorStateManager
from core.assessment.schema import (
    Question,
    MCQQuestion,
    NumericalQuestion,
    AssertionReasoningQuestion,
    ReactionCompletionQuestion,
    EquationBalancingQuestion,
    QuestionType,
)
from core.assessment.grader import AssessmentGrader
from core.assessment.manager import AssessmentManager, QuestionBankItem, SAMPLE_QUESTION_BANK


def test_question_schema_11_fields():
    """Verify all 11 required fields exist on Question and subclasses and serialize via to_dict()."""
    # 1. Base Question
    q = Question(
        id="q.base.01",
        concept_id="thermo.first_law",
        difficulty=3,
        type="conceptual",
        question="State the First Law of Thermodynamics.",
        answer="delta U = q + w",
        rubric="Must state energy conservation formula or words",
        hint="Relate internal energy to heat and work",
        explanation="Energy cannot be created or destroyed, only transformed.",
        common_misconceptions=["THERMO_SIGN_CONVENTION"],
        source="NCERT_CH6",
    )
    d = q.to_dict()
    assert d["id"] == "q.base.01"
    assert d["concept_id"] == "thermo.first_law"
    assert d["difficulty"] == 3
    assert d["type"] == "conceptual"
    assert d["question"] == "State the First Law of Thermodynamics."
    assert d["answer"] == "delta U = q + w"
    assert d["rubric"] == "Must state energy conservation formula or words"
    assert d["hint"] == "Relate internal energy to heat and work"
    assert d["explanation"] == "Energy cannot be created or destroyed, only transformed."
    assert d["common_misconceptions"] == ["THERMO_SIGN_CONVENTION"]
    assert d["source"] == "NCERT_CH6"

    # Backwards compatibility check
    assert d["question_id"] == "q.base.01"
    assert d["topic_id"] == "thermo.first_law"
    assert d["correct_answer"] == "delta U = q + w"


def test_all_question_subclasses_support_11_fields():
    """Verify MCQ, Numerical, AssertionReasoning, ReactionCompletion, and EquationBalancing support all 11 fields."""
    # MCQ
    mcq = MCQQuestion(
        id="q.mcq.01",
        concept_id="thermo.hess",
        difficulty=2,
        question="Which is a state function?",
        options=["Enthalpy", "Work", "Heat"],
        correct_index=0,
        rubric="Single correct option",
        hint="Does not depend on path",
        explanation="Enthalpy is a state function.",
        common_misconceptions=["STATE_VS_PATH_FUNCTION"],
        source="NCERT",
    )
    d_mcq = mcq.to_dict()
    assert d_mcq["id"] == "q.mcq.01"
    assert d_mcq["concept_id"] == "thermo.hess"
    assert d_mcq["difficulty"] == 2
    assert d_mcq["type"] == "mcq"
    assert d_mcq["question"] == "Which is a state function?"
    assert d_mcq["answer"] == "Enthalpy"
    assert d_mcq["rubric"] == "Single correct option"
    assert d_mcq["hint"] == "Does not depend on path"
    assert d_mcq["explanation"] == "Enthalpy is a state function."
    assert d_mcq["common_misconceptions"] == ["STATE_VS_PATH_FUNCTION"]
    assert d_mcq["source"] == "NCERT"
    assert d_mcq["options"] == ["Enthalpy", "Work", "Heat"]

    # Numerical
    num = NumericalQuestion(
        id="q.num.01",
        concept_id="thermo.hess_law",
        difficulty=3,
        question="Calculate delta H",
        expected_value=-110.5,
        tolerance=0.01,
        expected_unit="kJ/mol",
        rubric="Exact value within tolerance",
        hint="Invert equation 2",
        explanation="Hess law summation",
        common_misconceptions=["HESS_LAW_DIRECTION"],
        source="NCERT",
    )
    d_num = num.to_dict()
    assert d_num["id"] == "q.num.01"
    assert d_num["concept_id"] == "thermo.hess_law"
    assert d_num["difficulty"] == 3
    assert d_num["type"] == "numerical"
    assert d_num["answer"] == -110.5
    assert d_num["rubric"] == "Exact value within tolerance"
    assert d_num["hint"] == "Invert equation 2"
    assert d_num["explanation"] == "Hess law summation"
    assert d_num["common_misconceptions"] == ["HESS_LAW_DIRECTION"]
    assert d_num["source"] == "NCERT"

    # Assertion Reasoning
    ar = AssertionReasoningQuestion(
        id="q.ar.01",
        concept_id="thermo.gibbs",
        difficulty=4,
        question="Evaluate assertion and reason",
        assertion="Reaction is spontaneous",
        reason="delta G is negative",
        correct_option_index=0,
        rubric="Select correct combination",
        hint="Check delta G condition",
        explanation="delta G < 0 signifies spontaneity",
        common_misconceptions=["GIBBS_SIGN_CONFUSION"],
        source="NCERT",
    )
    d_ar = ar.to_dict()
    assert d_ar["id"] == "q.ar.01"
    assert d_ar["concept_id"] == "thermo.gibbs"
    assert d_ar["type"] == "assertion_reasoning"
    assert d_ar["assertion"] == "Reaction is spontaneous"
    assert d_ar["reason"] == "delta G is negative"
    assert d_ar["answer"] == d_ar["options"][0]

    # Reaction Completion
    rc = ReactionCompletionQuestion(
        id="q.rc.01",
        concept_id="inorganic.s_block",
        difficulty=2,
        question="Complete Na + H2O",
        reactants="Na + H2O",
        missing_products="NaOH + H2",
        rubric="Both products required",
        hint="Alkali metal reacts with water",
        explanation="Forms hydroxide and hydrogen gas",
        common_misconceptions=["REDOX_CONFUSION"],
        source="NCERT",
    )
    d_rc = rc.to_dict()
    assert d_rc["id"] == "q.rc.01"
    assert d_rc["concept_id"] == "inorganic.s_block"
    assert d_rc["type"] == "reaction_completion"
    assert d_rc["answer"] == "NaOH + H2"

    # Equation Balancing
    eb = EquationBalancingQuestion(
        id="q.eb.01",
        concept_id="inorganic.redox",
        difficulty=3,
        question="Balance Na + H2O -> NaOH + H2",
        unbalanced_equation="Na + H2O -> NaOH + H2",
        balanced_equation="2 Na + 2 H2O -> 2 NaOH + H2",
        rubric="Stoichiometric coefficients must match",
        hint="Balance H atoms first",
        explanation="2 Na, 4 H, 2 O on each side",
        common_misconceptions=["OXIDATION_STATE_ERROR"],
        source="NCERT",
    )
    d_eb = eb.to_dict()
    assert d_eb["id"] == "q.eb.01"
    assert d_eb["concept_id"] == "inorganic.redox"
    assert d_eb["type"] == "equation_balancing"
    assert d_eb["answer"] == "2 Na + 2 H2O -> 2 NaOH + H2"


def test_anti_leakage_sanitizer_removes_answers():
    """Verify AssessmentGrader.sanitize_for_client strips both answer and correct_answer."""
    q = MCQQuestion(
        id="q.mcq.leak",
        concept_id="thermo.hess",
        difficulty=2,
        question="What is Hess's law?",
        correct_answer="Path independence",
        explanation="State function property",
    )
    sanitized = AssessmentGrader.sanitize_for_client(q)
    assert "answer" not in sanitized
    assert "correct_answer" not in sanitized
    assert "explanation" not in sanitized
    assert "correct_index" not in sanitized
    assert sanitized["question"] == "What is Hess's law?"


def test_persistence_across_all_four_tables(tmp_path):
    """Verify Section 17 persistence across assessment, assessment_question, assessment_attempt, and score tables."""
    db_path = str(tmp_path / "assessment_test.db")
    sm = TutorStateManager(db_path=db_path)
    mgr = AssessmentManager(state_manager=sm, questions=SAMPLE_QUESTION_BANK)

    student_id = "student_sec17_01"
    concepts = ["thermo.hess_law", "thermo.gibbs"]

    # 1. Create Assessment Session -> Populates `assessment` and `assessment_question`
    assess_id = mgr.create_assessment_session(
        student_id=student_id,
        concepts=concepts,
        question_count=2,
    )
    assert assess_id.startswith("assess_")

    # Verify `assessment` table
    assess_rec = mgr.get_assessment(assess_id)
    assert assess_rec is not None
    assert assess_rec["assessment_id"] == assess_id
    assert assess_rec["student_id"] == student_id
    assert assess_rec["status"] == "IN_PROGRESS"
    assert json.loads(assess_rec["concepts_json"]) == concepts

    # Verify `assessment_question` table
    questions = mgr.get_assessment_questions(assess_id)
    assert len(questions) == 2
    q_ids = [q["question_id"] for q in questions]
    assert "thermo.hess.001" in q_ids
    assert "thermo.gibbs.001" in q_ids

    # Check that assessment_question contains all 11 schema fields
    sample_q = next(q for q in questions if q["question_id"] == "thermo.hess.001")
    assert sample_q["concept_id"] == "thermo.hess_law"
    assert sample_q["difficulty"] == 3
    assert sample_q["type"] == "numeric"
    assert "delta H" in sample_q["question"]
    assert sample_q["answer"] == "-110.5"
    assert sample_q["rubric"] != ""
    assert sample_q["hint"] != ""
    assert sample_q["explanation"] != ""
    assert "HESS_LAW_DIRECTION" in json.loads(sample_q["common_misconceptions"])
    assert sample_q["source"] == "NCERT"

    # 2. Submit Attempts -> Populates `assessment_attempt`
    att1 = mgr.submit_attempt(
        assessment_id=assess_id,
        student_id=student_id,
        question_id="thermo.hess.001",
        student_answer="-110.5",
    )
    assert att1["is_correct"] is True
    assert att1["score_fraction"] == 1.0

    att2 = mgr.submit_attempt(
        assessment_id=assess_id,
        student_id=student_id,
        question_id="thermo.gibbs.001",
        student_answer="delta G > 0",
    )
    assert att2["is_correct"] is False
    assert att2["detected_misconception"] == "GIBBS_SIGN_CONFUSION"

    # Verify `assessment_attempt` table
    attempts = mgr.get_assessment_attempts(assess_id)
    assert len(attempts) == 2
    assert attempts[0]["question_id"] == "thermo.hess.001"
    assert attempts[0]["is_correct"] == 1
    assert attempts[0]["score_fraction"] == 1.0
    assert attempts[1]["question_id"] == "thermo.gibbs.001"
    assert attempts[1]["is_correct"] == 0
    assert attempts[1]["score_fraction"] == 0.0

    # 3. Complete Assessment Session -> Updates `assessment` and populates `score`
    summary = mgr.complete_assessment_session(assess_id, student_id)
    assert summary["status"] == "COMPLETED"
    assert summary["score_percentage"] == 50.0
    assert "thermo.hess_law" in summary["strengths"]
    assert "thermo.gibbs" in summary["weaknesses"]

    # Verify `assessment` table updated
    assess_rec_completed = mgr.get_assessment(assess_id)
    assert assess_rec_completed["status"] == "COMPLETED"
    assert assess_rec_completed["score"] == 50.0
    assert assess_rec_completed["end_time"] != ""

    # Verify `score` table populated
    score_rec = mgr.get_assessment_score(assess_id)
    assert score_rec is not None
    assert score_rec["assessment_id"] == assess_id
    assert score_rec["student_id"] == student_id
    assert score_rec["total_score"] == 1.0
    assert score_rec["max_possible"] == 2.0
    assert score_rec["score_percentage"] == 50.0
    assert "thermo.hess_law" in json.loads(score_rec["strengths_json"])
    assert "thermo.gibbs" in json.loads(score_rec["weaknesses_json"])
    assert score_rec["completed_at"] != ""


def test_assessment_outcomes_become_learning_events(tmp_path):
    """Verify Section 17 requirement: assessment outcomes must become learning events updating student mastery."""
    db_path = str(tmp_path / "learning_events_test.db")
    sm = TutorStateManager(db_path=db_path)
    mgr = AssessmentManager(state_manager=sm, questions=SAMPLE_QUESTION_BANK)

    student_id = "student_sec17_events"
    assess_id = mgr.create_assessment_session(
        student_id=student_id,
        concepts=["thermo.hess_law"],
        question_count=1,
    )
    mgr.submit_attempt(
        assessment_id=assess_id,
        student_id=student_id,
        question_id="thermo.hess.001",
        student_answer="-110.5",
    )
    mgr.complete_assessment_session(assess_id, student_id)

    # 1. Verify LearningEvent recorded with source='assessment'
    events = sm.get_learning_events(student_id=student_id, concept_id="thermo.hess_law")
    assert len(events) >= 1
    event = events[0]
    assert event.source == "assessment"
    assert event.concept_id == "thermo.hess_law"
    assert event.question_id == "thermo.hess.001"
    assert event.correctness == "correct"

    # 2. Verify student_concept_mastery mutated
    mastery = sm.get_student_concept_mastery(student_id, "thermo.hess_law")
    assert mastery.exposure_count >= 1
    assert mastery.correct_count >= 1
    assert mastery.mastery > 0.0
