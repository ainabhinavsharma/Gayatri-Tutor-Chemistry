"""Gayatri AI — Assessment Question Schemas.

Defines schemas for MCQ, Numerical, Assertion-Reasoning, Reaction Completion,
and Equation Balancing questions.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class QuestionType(str, Enum):
    MCQ = "mcq"
    NUMERICAL = "numerical"
    ASSERTION_REASONING = "assertion_reasoning"
    REACTION_COMPLETION = "reaction_completion"
    EQUATION_BALANCING = "equation_balancing"


@dataclass
class Question:
    """Base question dataclass."""
    question_id: str
    topic_id: str
    difficulty: int  # 1 to 5
    question_text: str
    question_type: QuestionType = QuestionType.MCQ
    explanation: str = ""
    source_id: str = ""
    source_reference: str = ""
    grading_notes: dict[str, Any] = field(default_factory=dict)
    correct_answer: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "topic_id": self.topic_id,
            "type": self.question_type.value,
            "difficulty": self.difficulty,
            "question": self.question_text,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "source_id": self.source_id,
            "source_reference": self.source_reference,
            "grading_notes": self.grading_notes,
        }


@dataclass
class MCQQuestion(Question):
    """P7-T02: MCQ Question model."""
    options: list[str] = field(default_factory=list)
    correct_index: int = 0

    def __post_init__(self):
        self.question_type = QuestionType.MCQ
        if self.correct_answer is None and self.options and 0 <= self.correct_index < len(self.options):
            self.correct_answer = self.options[self.correct_index]

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["options"] = self.options
        d["correct_index"] = self.correct_index
        return d


@dataclass
class NumericalQuestion(Question):
    """P7-T03: Numerical Problem model."""
    expected_value: float = 0.0
    tolerance: float = 0.01
    expected_unit: str = ""
    solution_steps: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.question_type = QuestionType.NUMERICAL
        self.correct_answer = self.expected_value

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["expected_value"] = self.expected_value
        d["tolerance"] = self.tolerance
        d["expected_unit"] = self.expected_unit
        d["solution_steps"] = self.solution_steps
        return d


@dataclass
class AssertionReasoningQuestion(Question):
    """P7-T04: Assertion/Reasoning Question model."""
    assertion: str = ""
    reason: str = ""
    options: list[str] = field(default_factory=lambda: [
        "Both Assertion and Reason are true, and Reason is the correct explanation of Assertion.",
        "Both Assertion and Reason are true, but Reason is NOT the correct explanation of Assertion.",
        "Assertion is true, but Reason is false.",
        "Assertion is false, but Reason is true.",
        "Both Assertion and Reason are false."
    ])
    correct_option_index: int = 0

    def __post_init__(self):
        self.question_type = QuestionType.ASSERTION_REASONING
        if 0 <= self.correct_option_index < len(self.options):
            self.correct_answer = self.options[self.correct_option_index]

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["assertion"] = self.assertion
        d["reason"] = self.reason
        d["options"] = self.options
        d["correct_option_index"] = self.correct_option_index
        return d


@dataclass
class ReactionCompletionQuestion(Question):
    """P7-T05: Reaction Completion Question model."""
    reactants: str = ""
    missing_products: str = ""
    conditions: str = ""

    def __post_init__(self):
        self.question_type = QuestionType.REACTION_COMPLETION
        self.correct_answer = self.missing_products

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["reactants"] = self.reactants
        d["missing_products"] = self.missing_products
        d["conditions"] = self.conditions
        return d


@dataclass
class EquationBalancingQuestion(Question):
    """P7-T06: Equation Balancing Question model."""
    unbalanced_equation: str = ""
    balanced_equation: str = ""

    def __post_init__(self):
        self.question_type = QuestionType.EQUATION_BALANCING
        self.correct_answer = self.balanced_equation

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["unbalanced_equation"] = self.unbalanced_equation
        d["balanced_equation"] = self.balanced_equation
        return d
