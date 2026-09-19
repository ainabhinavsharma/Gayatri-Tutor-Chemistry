"""Gayatri AI - Phase 2 Acceptance Test Suite.

Tests structured Chemistry answer evaluator:
- Keyword-based correctness removal
- Structured evaluation contract
- Deterministic evaluators (MCQ, numeric, formula, reaction, short answer)
- Tolerance and unit error detection
- Ambiguous answer 'uncertain' fallback
- Evidence trail generation
"""

import pytest
from core.tutor.evaluator import StudentAnswerEvaluator, EvaluationResult


def test_keyword_yes_cannot_prove_random_question_correct():
    """P2-T01: 'yes' without question context returns 'uncertain'."""
    res = StudentAnswerEvaluator.evaluate("yes")
    assert res.correctness == "uncertain"
    assert res.confidence == 0.0
    assert len(res.evidence) > 0


def test_keyword_400_cannot_prove_random_question_correct():
    """P2-T01: '400' without question context returns 'uncertain'."""
    res = StudentAnswerEvaluator.evaluate("400")
    assert res.correctness == "uncertain"
    assert res.confidence == 0.0


def test_numeric_within_tolerance_correct():
    """P2-T03: Numeric answer within 5% tolerance returns 'correct'."""
    res = StudentAnswerEvaluator.evaluate(
        user_answer="402 J",
        expected_answer="400.0",
        question_type="numeric",
        tolerance=0.05
    )
    assert res.correctness == "correct"
    assert res.error_type == "none"


def test_numeric_outside_tolerance_incorrect():
    """P2-T03: Numeric answer outside tolerance returns 'incorrect' and arithmetic error."""
    res = StudentAnswerEvaluator.evaluate(
        user_answer="550 J",
        expected_answer="400.0",
        question_type="numeric",
        tolerance=0.05
    )
    assert res.correctness == "incorrect"
    assert res.error_type == "arithmetic"


def test_numeric_wrong_unit_returns_unit_error():
    """P2-T03: Correct number with wrong unit returns 'partially_correct' and 'unit_error'."""
    res = StudentAnswerEvaluator.evaluate(
        user_answer="400 calories",
        expected_answer="400.0",
        question_type="numeric",
        tolerance=0.05,
        expected_unit="J"
    )
    assert res.correctness == "partially_correct"
    assert res.error_type == "unit_error"


def test_mcq_evaluation():
    """P2-T03: MCQ option matching."""
    res_correct = StudentAnswerEvaluator.evaluate(
        user_answer="Option B",
        expected_answer="B",
        question_type="mcq"
    )
    assert res_correct.correctness == "correct"

    res_incorrect = StudentAnswerEvaluator.evaluate(
        user_answer="Option A",
        expected_answer="B",
        question_type="mcq"
    )
    assert res_incorrect.correctness == "incorrect"


def test_formula_and_reaction_evaluation():
    """P2-T03: Formula and reaction string normalization and evaluation."""
    res_formula = StudentAnswerEvaluator.evaluate(
        user_answer="delta U = q + w",
        expected_answer="delta U = q + w",
        question_type="formula"
    )
    assert res_formula.correctness == "correct"

    res_reaction = StudentAnswerEvaluator.evaluate(
        user_answer="2H2 + O2 -> 2H2O",
        expected_answer="2H2 + O2 -> 2H2O",
        question_type="reaction"
    )
    assert res_reaction.correctness == "correct"


def test_ambiguous_answer_returns_uncertain():
    """P2-T04: Ambiguous/short answer without match returns 'uncertain' (NOT 'incorrect')."""
    res = StudentAnswerEvaluator.evaluate("idk maybe")
    assert res.correctness == "uncertain"


def test_evaluation_evidence_trail():
    """P2-T05: Evaluator generates evidence trail."""
    res = StudentAnswerEvaluator.evaluate(
        user_answer="Internal energy change delta U equals heat plus work",
        expected_answer="delta U = q + w",
        question_type="short_answer",
        rubric="internal energy heat work"
    )
    assert len(res.evidence) > 0
