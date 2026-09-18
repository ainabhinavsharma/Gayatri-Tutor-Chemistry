"""Tests for Phase 7 — Assessment Engine."""
from __future__ import annotations

import pytest

from core.assessment.schema import (
    AssertionReasoningQuestion,
    EquationBalancingQuestion,
    MCQQuestion,
    NumericalQuestion,
    QuestionType,
    ReactionCompletionQuestion,
)
from core.assessment.balancing import EquationBalancingEngine
from core.assessment.grader import AssessmentGrader
from core.assessment.generator import TestGenerator, DEFAULT_QUESTION_POOL
from core.assessment.adaptive import AdaptiveTestSelector


class TestQuestionSchemas:
    def test_mcq_schema(self):
        q = MCQQuestion(
            question_id="q1",
            topic_id="first_law",
            difficulty=1,
            question_text="What is First Law?",
            options=["q + w", "PV=nRT"],
            correct_index=0,
        )
        assert q.question_type == QuestionType.MCQ
        assert q.correct_answer == "q + w"
        d = q.to_dict()
        assert d["options"] == ["q + w", "PV=nRT"]

    def test_numerical_schema(self):
        q = NumericalQuestion(
            question_id="q2",
            topic_id="heat_capacity",
            difficulty=2,
            question_text="Calculate delta U",
            expected_value=250.0,
            expected_unit="J",
        )
        assert q.question_type == QuestionType.NUMERICAL
        assert q.correct_answer == 250.0

    def test_assertion_reasoning_schema(self):
        q = AssertionReasoningQuestion(
            question_id="q3",
            topic_id="spontaneity",
            difficulty=3,
            question_text="Evaluate AR",
            assertion="delta G is negative",
            reason="Spontaneous process",
            correct_option_index=0,
        )
        assert q.question_type == QuestionType.ASSERTION_REASONING
        assert len(q.options) == 5

    def test_equation_balancing_schema(self):
        q = EquationBalancingQuestion(
            question_id="q4",
            topic_id="s_block",
            difficulty=2,
            question_text="Balance equation",
            unbalanced_equation="Na + H2O -> NaOH + H2",
            balanced_equation="2 Na + 2 H2O -> 2 NaOH + H2",
        )
        assert q.question_type == QuestionType.EQUATION_BALANCING


class TestEquationBalancingEngine:
    def test_balanced_equation(self):
        is_bal, msg = EquationBalancingEngine.verify_balance("2 Na + 2 H2O -> 2 NaOH + H2")
        assert is_bal is True
        assert "balanced" in msg.lower()

    def test_unbalanced_equation(self):
        is_bal, msg = EquationBalancingEngine.verify_balance("Na + H2O -> NaOH + H2")
        assert is_bal is False
        assert "imbalanced" in msg.lower()

    def test_invalid_equation_format(self):
        is_bal, msg = EquationBalancingEngine.verify_balance("invalid text without arrow")
        assert is_bal is False


class TestAssessmentGraderAndAntiLeakage:
    def test_anti_leakage_sanitizer(self):
        q = MCQQuestion(
            question_id="q1",
            topic_id="first_law",
            difficulty=1,
            question_text="What is First Law?",
            options=["q + w", "PV=nRT"],
            correct_index=0,
            explanation="Secret explanation text",
            grading_notes={"secret": "key"},
        )
        sanitized = AssessmentGrader.sanitize_for_client(q)
        assert "correct_answer" not in sanitized
        assert "explanation" not in sanitized
        assert "grading_notes" not in sanitized
        assert "correct_index" not in sanitized
        assert sanitized["question"] == "What is First Law?"
        assert sanitized["options"] == ["q + w", "PV=nRT"]

    def test_grade_mcq_correct(self):
        q = MCQQuestion(
            question_id="q1",
            topic_id="first_law",
            difficulty=1,
            question_text="First Law?",
            options=["A", "B"],
            correct_index=0,
        )
        is_corr, score, feedback = AssessmentGrader.grade_answer(q, "0")
        assert is_corr is True
        assert score == 1.0

    def test_grade_numerical_within_tolerance(self):
        q = NumericalQuestion(
            question_id="q2",
            topic_id="heat_capacity",
            difficulty=2,
            question_text="Calculate",
            expected_value=250.0,
            tolerance=0.02,
        )
        is_corr, score, _ = AssessmentGrader.grade_answer(q, "250.5")
        assert is_corr is True

    def test_grade_equation_balancing(self):
        q = EquationBalancingQuestion(
            question_id="q4",
            topic_id="s_block",
            difficulty=2,
            question_text="Balance equation",
            unbalanced_equation="Na + H2O -> NaOH + H2",
            balanced_equation="2 Na + 2 H2O -> 2 NaOH + H2",
        )
        is_corr, score, _ = AssessmentGrader.grade_answer(q, "2 Na + 2 H2O -> 2 NaOH + H2")
        assert is_corr is True


class TestTestGeneratorAndAdaptive:
    def test_generate_chapter_test(self):
        paper = TestGenerator.generate_chapter_test("Thermodynamics", "first_law", 2, 15)
        assert paper.chapter == "Thermodynamics"
        assert len(paper.questions) == 2
        assert paper.is_mock_test is False

    def test_generate_full_mock_test(self):
        paper = TestGenerator.generate_full_mock_test("Full Chemistry Mock", 3, 45)
        assert paper.is_mock_test is True
        assert len(paper.questions) == 3

    def test_adaptive_selection(self):
        q = AdaptiveTestSelector.select_next_question(DEFAULT_QUESTION_POOL, mastery_score=0.9, recent_correctness=True)
        assert q is not None
        assert q.difficulty >= 3
