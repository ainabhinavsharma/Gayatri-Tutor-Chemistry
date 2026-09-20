"""Gayatri AI — Assessment Grader & Anti-Leakage Protection (P7-T10).

Grades submitted answers deterministically on the backend and strips answer keys
before returning question structures to the frontend UI.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

from core.assessment.balancing import EquationBalancingEngine
from core.assessment.schema import (
    AssertionReasoningQuestion,
    EquationBalancingQuestion,
    MCQQuestion,
    NumericalQuestion,
    Question,
    QuestionType,
    ReactionCompletionQuestion,
)

logger = logging.getLogger("gayatri.assessment.grader")


class AssessmentGrader:
    """Authoritative backend grader with anti-leakage protection."""

    @staticmethod
    def sanitize_for_client(question: Question) -> dict[str, Any]:
        """Strip correct_answer, explanation, and internal grading notes before client transmission."""
        d = question.to_dict()
        # Anti-leakage: remove answer keys & explanations
        d.pop("correct_answer", None)
        d.pop("answer", None)
        d.pop("explanation", None)
        d.pop("grading_notes", None)
        d.pop("correct_index", None)
        d.pop("correct_option_index", None)
        d.pop("expected_value", None)
        d.pop("missing_products", None)
        d.pop("balanced_equation", None)
        return d

    @classmethod
    def grade_answer(cls, question: Question, student_answer: Any) -> tuple[bool, float, str]:
        """Grade a student submission against the backend question model.
        Returns (is_correct, score_fraction, feedback).
        """
        if student_answer is None or str(student_answer).strip() == "":
            return False, 0.0, "No answer provided."

        qtype = question.question_type

        # 1. MCQ Grading
        if qtype == QuestionType.MCQ:
            ans = str(student_answer).strip()
            if isinstance(question, MCQQuestion):
                if ans.isdigit():
                    idx = int(ans)
                    is_corr = (idx == question.correct_index)
                else:
                    is_corr = (ans.lower() == str(question.correct_answer).lower())
            else:
                is_corr = (ans.lower() == str(question.correct_answer).lower())

            score = 1.0 if is_corr else 0.0
            feedback = "Correct!" if is_corr else f"Incorrect. Correct answer was: {question.correct_answer}"
            return is_corr, score, feedback

        # 2. Numerical Grading
        elif qtype == QuestionType.NUMERICAL:
            try:
                exp = float(question.correct_answer)
            except (ValueError, TypeError) as exp_err:
                logger.error(f"Grader: question {getattr(question, 'question_id', 'unknown')} has invalid correct_answer: {exp_err}")
                return False, 0.0, "Internal error: question configuration invalid."

            try:
                val = float(re_extract_number(str(student_answer)))
                tol = getattr(question, "tolerance", 0.05) * max(1.0, abs(exp))

                if math.isclose(val, exp, abs_tol=tol):
                    return True, 1.0, "Correct calculation!"
                else:
                    return False, 0.0, f"Incorrect numerical result. Expected approx {exp}."
            except (ValueError, TypeError):
                return False, 0.0, "Invalid numerical answer format. Expected a number."

        # 3. Assertion / Reasoning Grading
        elif qtype == QuestionType.ASSERTION_REASONING:
            ans = str(student_answer).strip()
            if isinstance(question, AssertionReasoningQuestion):
                if ans.isdigit():
                    is_corr = (int(ans) == question.correct_option_index)
                else:
                    is_corr = (ans.lower() == str(question.correct_answer).lower())
            else:
                is_corr = (ans.lower() == str(question.correct_answer).lower())

            score = 1.0 if is_corr else 0.0
            return is_corr, score, "Correct reasoning!" if is_corr else "Incorrect evaluation of assertion/reason."

        # 4. Equation Balancing Grading (Deterministic)
        elif qtype == QuestionType.EQUATION_BALANCING:
            ans = str(student_answer).strip()
            is_bal, msg = EquationBalancingEngine.verify_balance(ans)
            score = 1.0 if is_bal else 0.0
            return is_bal, score, msg

        # 5. Reaction Completion Grading
        elif qtype == QuestionType.REACTION_COMPLETION:
            ans = str(student_answer).strip().lower()
            exp = str(question.correct_answer).strip().lower()
            is_corr = (ans in exp or exp in ans)
            score = 1.0 if is_corr else 0.0
            return is_corr, score, "Correct product completion!" if is_corr else f"Incorrect products. Expected: {question.correct_answer}"

        return False, 0.0, "Unknown question type."


def re_extract_number(text: str) -> str:
    """Extract first floating-point or integer number string from text."""
    import re
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return match.group(0) if match else "0.0"
