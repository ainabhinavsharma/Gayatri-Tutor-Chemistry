"""Gayatri AI — Prompt System 2.0 Pydantic and JSON Output Schemas.

Defines strict schemas for LLM internal generation tasks, structured outputs,
Socratic hints, misconception diagnosis, problem generation, and evaluations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SocraticHintResponse(BaseModel):
    """Schema for structured Socratic hint generation."""

    hint_tier: int = Field(..., ge=1, le=5, description="Hint tier from 1 (gentle direction) to 5 (near solution)")
    guiding_question: str = Field(..., description="Socratic guiding question encouraging student thinking")
    conceptual_clue: str = Field(..., description="Key concept or law referenced in the hint without giving answer")
    prevents_answer_leakage: bool = Field(True, description="Safety flag confirming no direct numerical answer leaked")


class MisconceptionDiagnosisResponse(BaseModel):
    """Schema for structured misconception diagnosis generation."""

    misconception_code: str = Field(..., description="Standardized misconception code, e.g., THERMO_SIGN_CONVENTION")
    is_misconception_present: bool = Field(..., description="True if student response exhibits a known misconception")
    root_cause_explanation: str = Field(..., description="Clear explanation of the error in reasoning")
    remediation_strategy: str = Field(..., description="Targeted pedagogical steps to re-align conceptual understanding")


class ProblemGenerationResponse(BaseModel):
    """Schema for structured problem generation."""

    problem_id: str = Field(..., description="Unique problem identifier")
    concept_id: str = Field(..., description="Target concept ID")
    difficulty: str = Field(..., description="Difficulty level: beginner, intermediate, advanced, or exam")
    question_text: str = Field(..., description="Complete statement of the problem or question")
    given_data: Dict[str, str] = Field(default_factory=dict, description="Key variables, given quantities, or conditions")
    target_variable: str = Field(..., description="What the student needs to solve for or answer")
    hints_available: List[str] = Field(default_factory=list, description="Sequence of hint strings")


class AnswerEvaluationResponse(BaseModel):
    """Schema for structured answer evaluation."""

    is_correct: bool = Field(..., description="Evaluation outcome: true if correct, false otherwise")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the evaluation assessment")
    feedback_text: str = Field(..., description="Constructive feedback for the student")
    detected_misconceptions: List[str] = Field(default_factory=list, description="Codes of detected misconceptions")
    mastery_delta: float = Field(0.0, description="Suggested change in student concept mastery score")


class ContextualRewriteResponse(BaseModel):
    """Schema for contextual query rewriting."""

    original_query: str = Field(..., description="Raw student query")
    standalone_query: str = Field(..., description="De-anaphorized, standalone chemistry query")
    resolved_entities: List[str] = Field(default_factory=list, description="Chemical entities resolved from context")
