"""Gayatri AI — Assessment Question Schemas.

Defines schemas for MCQ, Numerical, Assertion-Reasoning, Reaction Completion,
and Equation Balancing questions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QuestionType(str, Enum):
    MCQ = "mcq"
    NUMERICAL = "numerical"
    ASSERTION_REASONING = "assertion_reasoning"
    REACTION_COMPLETION = "reaction_completion"
    EQUATION_BALANCING = "equation_balancing"


@dataclass
class Question:
    """Base question dataclass supporting Section 17 schema and legacy fields."""
    question_id: str = ""
    topic_id: str = ""
    difficulty: int = 1  # 1 to 5
    question_text: str = ""
    question_type: QuestionType = QuestionType.MCQ
    explanation: str = ""
    source_id: str = "NCERT"
    source_reference: str = ""
    grading_notes: dict[str, Any] = field(default_factory=dict)
    correct_answer: Any = None
    rubric: str = ""
    hint: str = ""
    common_misconceptions: list[str] = field(default_factory=list)
    # Section 17 primary field aliases
    id: str = ""
    concept_id: str = ""
    type: str = ""
    question: str = ""
    answer: Any = None
    source: str = ""

    def __post_init__(self):
        # Synchronize Section 17 primary fields and legacy fields
        if not self.id and self.question_id:
            self.id = self.question_id
        elif not self.question_id and self.id:
            self.question_id = self.id

        if not self.concept_id and self.topic_id:
            self.concept_id = self.topic_id
        elif not self.topic_id and self.concept_id:
            self.topic_id = self.concept_id

        if not self.question and self.question_text:
            self.question = self.question_text
        elif not self.question_text and self.question:
            self.question_text = self.question

        if self.answer is None and self.correct_answer is not None:
            self.answer = self.correct_answer
        elif self.correct_answer is None and self.answer is not None:
            self.correct_answer = self.answer

        if not self.source and self.source_id:
            self.source = self.source_id
        elif not self.source_id and self.source:
            self.source_id = self.source

        if not self.type and self.question_type:
            self.type = self.question_type.value if isinstance(self.question_type, Enum) else str(self.question_type)
        elif not self.question_type and self.type:
            try:
                self.question_type = QuestionType(self.type)
            except Exception:
                self.question_type = QuestionType.MCQ

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "concept_id": self.concept_id,
            "difficulty": self.difficulty,
            "type": self.type or (self.question_type.value if isinstance(self.question_type, Enum) else str(self.question_type)),
            "question": self.question,
            "answer": self.answer if self.answer is not None else self.correct_answer,
            "rubric": self.rubric,
            "hint": self.hint,
            "explanation": self.explanation,
            "common_misconceptions": list(self.common_misconceptions),
            "source": self.source,
            # Backwards-compatibility aliases:
            "question_id": self.question_id,
            "topic_id": self.topic_id,
            "question_text": self.question_text,
            "correct_answer": self.correct_answer,
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
        self.type = "mcq"
        if self.correct_answer is None and self.options and 0 <= self.correct_index < len(self.options):
            self.correct_answer = self.options[self.correct_index]
        super().__post_init__()

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
        self.type = "numerical"
        if self.correct_answer is None:
            self.correct_answer = self.expected_value
        super().__post_init__()

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
        self.type = "assertion_reasoning"
        if 0 <= self.correct_option_index < len(self.options) and self.correct_answer is None:
            self.correct_answer = self.options[self.correct_option_index]
        super().__post_init__()

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
        self.type = "reaction_completion"
        if self.correct_answer is None:
            self.correct_answer = self.missing_products
        super().__post_init__()

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
        self.type = "equation_balancing"
        if self.correct_answer is None:
            self.correct_answer = self.balanced_equation
        super().__post_init__()

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["unbalanced_equation"] = self.unbalanced_equation
        d["balanced_equation"] = self.balanced_equation
        return d
