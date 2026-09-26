"""Gayatri AI — Prompt Families & Modular Builders for Prompt System 2.0.

Provides modular prompt builders for all 17 standardized action families.
Each builder dynamically composes the 7-layer structure:
  1. SYSTEM POLICY
  2. TASK POLICY
  3. STUDENT STATE
  4. LEARNING OBJECTIVE
  5. EVIDENCE PACK
  6. USER QUERY
  7. OUTPUT SCHEMA
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ActionFamily(str, Enum):
    """Standardized action families for Prompt System 2.0."""
    EXPLAIN_CONCEPT = "EXPLAIN_CONCEPT"
    WHY_QUESTION = "WHY_QUESTION"
    DEFINITION = "DEFINITION"
    FORMULA_EXPLANATION = "FORMULA_EXPLANATION"
    DERIVATION_STEP = "DERIVATION_STEP"
    NUMERICAL_PROBLEM = "NUMERICAL_PROBLEM"
    SOCRATIC_HINT = "SOCRATIC_HINT"
    ANSWER_CHECK = "ANSWER_CHECK"
    MISCONCEPTION_REMEDIATION = "MISCONCEPTION_REMEDIATION"
    REVISION_RECAP = "REVISION_RECAP"
    PRACTICE_QUESTION = "PRACTICE_QUESTION"
    QUIZ_GENERATION = "QUIZ_GENERATION"
    EXAM_PREP = "EXAM_PREP"
    SUMMARY = "SUMMARY"
    CONTEXTUAL_REWRITE = "CONTEXTUAL_REWRITE"
    CONFUSION_RESOLVE = "CONFUSION_RESOLVE"
    GENERAL_HELP = "GENERAL_HELP"


# Action-family specific instructions
ACTION_FAMILY_DIRECTIVES: Dict[ActionFamily, str] = {
    ActionFamily.EXPLAIN_CONCEPT: (
        "TASK POLICY: Structure explanation into:\n"
        "1. Everyday Analogy (intuitive physical connection)\n"
        "2. Core Chemical Principle (precise NCERT conceptual definition)\n"
        "3. Worked Example or Application\n"
        "4. Single Checking Question (verify comprehension before proceeding)."
    ),
    ActionFamily.WHY_QUESTION: (
        "TASK POLICY: Answer the 'Why' question by addressing the underlying chemical cause or "
        "thermodynamic drive (e.g. energy minimization, entropy increase, electronic stability). "
        "End with a reflection prompt for the student."
    ),
    ActionFamily.DEFINITION: (
        "TASK POLICY: State the precise NCERT definition clearly. Highlight key terms, SI units, "
        "and typical contextual usage. Follow with a simple true/false check."
    ),
    ActionFamily.FORMULA_EXPLANATION: (
        "TASK POLICY: Break down the mathematical formula term by term. Define each symbol, "
        "specify its standard SI units, and explain the physical significance of the relationship."
    ),
    ActionFamily.DERIVATION_STEP: (
        "TASK POLICY: Walk through the mathematical or logical derivation step-by-step. "
        "Explicitly state assumptions and law references at each step."
    ),
    ActionFamily.NUMERICAL_PROBLEM: (
        "TASK POLICY: Pose a calibrated numerical problem. State given variables clearly, specify what to solve, "
        "and instruct student to show units and sign reasoning. DO NOT reveal the numerical answer."
    ),
    ActionFamily.SOCRATIC_HINT: (
        "TASK POLICY: Provide a targeted Socratic hint based on the student's current hint tier. "
        "Point out relevant laws or relationships without solving the equation or revealing the answer."
    ),
    ActionFamily.ANSWER_CHECK: (
        "TASK POLICY: Evaluate the student's answer constructively. Praise effort, identify correct parts, "
        "highlight any error in sign/units/logic, and ask them to refine their answer. ZERO ANSWER LEAKAGE."
    ),
    ActionFamily.MISCONCEPTION_REMEDIATION: (
        "TASK POLICY: Directly address the active misconception. Contrast the flawed intuition with the correct "
        "NCERT physical reality using a clear counter-example. Pose a quick diagnostic micro-question."
    ),
    ActionFamily.REVISION_RECAP: (
        "TASK POLICY: Provide a concise high-yield revision recap of key definitions, formulas, and common pitfalls. "
        "Suggest 2 practice questions."
    ),
    ActionFamily.PRACTICE_QUESTION: (
        "TASK POLICY: Present ONE calibrated practice question appropriate for the student's mastery level. "
        "Require the student to explain their step-by-step reasoning."
    ),
    ActionFamily.QUIZ_GENERATION: (
        "TASK POLICY: Generate a 3-question mini-quiz covering conceptual understanding, numerical application, "
        "and assertion-reasoning for the topic."
    ),
    ActionFamily.EXAM_PREP: (
        "TASK POLICY: Present an exam-style question (CBSE / JEE / NEET alignment) including marking criteria "
        "and key points required for full marks."
    ),
    ActionFamily.SUMMARY: (
        "TASK POLICY: Provide a complete lesson summary: key takeaways, mastered concepts, resolved misconceptions, "
        "and recommended next topic."
    ),
    ActionFamily.CONTEXTUAL_REWRITE: (
        "TASK POLICY: Rewrite the student query to be fully self-contained by resolving pronouns and implicit references "
        "from past chat context. Output JSON matching ContextualRewriteResponse."
    ),
    ActionFamily.CONFUSION_RESOLVE: (
        "TASK POLICY: Acknowledge the student's confusion empathetically. Deconstruct the confusing concept into "
        "two simpler parts and address each sequentially."
    ),
    ActionFamily.GENERAL_HELP: (
        "TASK POLICY: Warmly guide the student on how to use Gayatri Chemistry Tutor for Class 11 & 12 NCERT Chemistry."
    ),
}
