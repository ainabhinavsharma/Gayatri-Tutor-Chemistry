"""Gayatri AI — Assessment Test Generator (P7-T07 & P7-T08).

Generates single-chapter tests or configurable multi-chapter mock tests.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from core.assessment.schema import (
    AssertionReasoningQuestion,
    EquationBalancingQuestion,
    MCQQuestion,
    NumericalQuestion,
    Question,
    QuestionType,
    ReactionCompletionQuestion,
)


@dataclass
class TestPaper:
    """A generated assessment test containing multiple questions."""
    test_id: str
    title: str
    topic_id: str
    chapter: str
    questions: list[Question] = field(default_factory=list)
    time_limit_minutes: int = 30
    is_mock_test: bool = False

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "title": self.title,
            "topic_id": self.topic_id,
            "chapter": self.chapter,
            "question_count": len(self.questions),
            "questions": [q.to_dict() for q in self.questions],
            "time_limit_minutes": self.time_limit_minutes,
            "is_mock_test": self.is_mock_test,
        }


# Default seed question pool
DEFAULT_QUESTION_POOL: list[Question] = [
    MCQQuestion(
        question_id="q_thermo_mcq_1",
        topic_id="first_law",
        difficulty=1,
        question_text="Which of the following equations represents the First Law of Thermodynamics?",
        options=["delta U = q + w", "delta G = delta H - T delta S", "Cp - Cv = R", "PV = nRT"],
        correct_index=0,
        explanation="First Law of Thermodynamics states delta U = q + w.",
        source_id="NCERT_CH6",
    ),
    NumericalQuestion(
        question_id="q_thermo_num_1",
        topic_id="heat_capacity",
        difficulty=2,
        question_text="A system absorbs 400 J of heat and does 150 J of work. Calculate the change in internal energy (delta U) in Joules.",
        expected_value=250.0,
        tolerance=1.0,
        expected_unit="J",
        solution_steps=["delta U = q + w", "q = +400 J", "w = -150 J (work done BY system)", "delta U = 400 - 150 = 250 J"],
        explanation="delta U = q + w = 400 - 150 = 250 J.",
        source_id="NCERT_CH6",
    ),
    AssertionReasoningQuestion(
        question_id="q_thermo_ar_1",
        topic_id="spontaneity",
        difficulty=3,
        question_text="Evaluate the Assertion and Reason regarding spontaneity.",
        assertion="A process is spontaneous if delta G is negative.",
        reason="Gibbs free energy change combines enthalpy and entropy factors (delta G = delta H - T delta S).",
        correct_option_index=0,
        explanation="Both Assertion and Reason are true, and Reason is the correct explanation.",
        source_id="NCERT_CH6",
    ),
    EquationBalancingQuestion(
        question_id="q_inorg_eq_1",
        topic_id="s_block_elements",
        difficulty=2,
        question_text="Balance the chemical equation for the reaction of sodium metal with water: Na + H2O -> NaOH + H2",
        unbalanced_equation="Na + H2O -> NaOH + H2",
        balanced_equation="2 Na + 2 H2O -> 2 NaOH + H2",
        explanation="2 atoms of Na, 4 of H, and 2 of O on both sides.",
        source_id="NCERT_CH10",
    ),
    ReactionCompletionQuestion(
        question_id="q_inorg_rc_1",
        topic_id="s_block_elements",
        difficulty=2,
        question_text="Complete the products for the reaction: Na + H2O -> ?",
        reactants="Na + H2O",
        missing_products="NaOH + H2",
        explanation="Sodium reacts with water to form sodium hydroxide and hydrogen gas.",
        source_id="NCERT_CH10",
    ),
]


class TestGenerator:
    """Generates chapter tests and multi-chapter mock tests."""

    @staticmethod
    def generate_chapter_test(
        chapter: str = "Thermodynamics",
        topic_id: str = "first_law",
        question_count: int = 5,
        time_limit_minutes: int = 20,
    ) -> TestPaper:
        """P7-T07: Generate a chapter test."""
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        matching = [q for q in DEFAULT_QUESTION_POOL if q.topic_id == topic_id or topic_id == "all"]
        others = [q for q in DEFAULT_QUESTION_POOL if q not in matching]
        selected = (matching + others)[:question_count]

        return TestPaper(
            test_id=test_id,
            title=f"{chapter} Chapter Test",
            topic_id=topic_id,
            chapter=chapter,
            questions=selected,
            time_limit_minutes=time_limit_minutes,
            is_mock_test=False,
        )

    @staticmethod
    def generate_full_mock_test(
        title: str = "Class 11 Chemistry Full Mock Test",
        question_count: int = 5,
        time_limit_minutes: int = 60,
    ) -> TestPaper:
        """P7-T08: Generate a multi-chapter full mock test."""
        test_id = f"mock_{uuid.uuid4().hex[:8]}"
        questions = DEFAULT_QUESTION_POOL[:question_count]

        return TestPaper(
            test_id=test_id,
            title=title,
            topic_id="all_chapters",
            chapter="Multi-Chapter",
            questions=questions,
            time_limit_minutes=time_limit_minutes,
            is_mock_test=True,
        )
