"""Gayatri AI - Structured Chemistry Student Answer Evaluator (Phase 2).

Replaces legacy keyword matching with a structured, context-aware,
evidence-driven answer evaluation engine for Chemistry turns.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("gayatri.tutor.evaluator")

# Words that alone CANNOT establish correctness without question context (P2-T01)
GENERIC_AMBIGUOUS_WORDS = {
    "yes", "no", "true", "false", "correct", "equal", "ok", "sure",
    "400", "200", "50", "0", "1", "2", "3", "4", "100", "idk", "dunno", "maybe"
}


@dataclass
class EvaluationResult:
    """Structured evaluation metadata for a student answer (P0-02 / P2-T02)."""
    correctness: str  # "correct", "partially_correct", "incorrect", "uncertain"
    confidence: float  # 0.0 to 1.0
    concept_understanding: str  # "sound", "shaky", "misconception", "unknown"
    error_type: str  # "none", "conceptual", "arithmetic", "formula_misuse", "unit_error", "reaction", "notation", "other"
    misconception: Optional[str] = None
    recommended_action: str = "proceed"  # "advance", "reinforce", "remediate", "prerequisite_review"
    difficulty_delta: float = 0.0
    evidence: List[str] = field(default_factory=list)
    next_difficulty_change: str = "maintain"  # "increase", "maintain", "decrease" (legacy compat)

    def to_dict(self) -> dict:
        return {
            "correctness": self.correctness,
            "confidence": self.confidence,
            "concept_understanding": self.concept_understanding,
            "error_type": self.error_type,
            "misconception": self.misconception or "",
            "recommended_action": self.recommended_action,
            "difficulty_delta": self.difficulty_delta,
            "evidence": self.evidence,
            "next_difficulty_change": self.next_difficulty_change,
        }


class StudentAnswerEvaluator:
    """Context-aware, evidence-driven student answer evaluator (Phase 2)."""

    @staticmethod
    def evaluate(
        user_answer: str,
        expected_answer: str = "",
        question_type: str = "conceptual",
        rubric: str = "",
        tolerance: float = 0.05,
        expected_unit: str = ""
    ) -> EvaluationResult:
        """Evaluate student answer using structured criteria & evidence (P2-T01 to P2-T05)."""
        try:
            text = user_answer.strip()
            clean_text = text.lower()

            if not clean_text:
                return EvaluationResult(
                    correctness="uncertain",
                    confidence=0.0,
                    concept_understanding="unknown",
                    error_type="other",
                    recommended_action="reinforce",
                    evidence=["Empty answer submitted"]
                )

            # P2-T01 & P2-T04: Generic single-word / number answers without context return 'uncertain'
            if not expected_answer and not rubric:
                if clean_text in GENERIC_AMBIGUOUS_WORDS or clean_text.isdigit():
                    return EvaluationResult(
                        correctness="uncertain",
                        confidence=0.0,
                        concept_understanding="unknown",
                        error_type="other",
                        recommended_action="reinforce",
                        next_difficulty_change="maintain",
                        evidence=[f"Ambiguous or generic answer '{text}' provided without question context"]
                    )

            # -- 1. MCQ Evaluator --
            if question_type == "mcq" and expected_answer:
                exp_clean = expected_answer.strip().lower()
                # Extract option letter e.g., 'A', '(b)', 'Option C'
                user_opt = re.sub(r'[^a-d]', '', clean_text[:5])
                exp_opt = re.sub(r'[^a-d]', '', exp_clean[:5])

                if user_opt and user_opt == exp_opt:
                    return EvaluationResult(
                        correctness="correct",
                        confidence=1.0,
                        concept_understanding="sound",
                        error_type="none",
                        recommended_action="advance",
                        next_difficulty_change="increase",
                        evidence=[f"Selected correct option '{user_answer}' matching '{expected_answer}'"]
                    )
                elif exp_clean in clean_text or clean_text in exp_clean:
                    return EvaluationResult(
                        correctness="correct",
                        confidence=0.9,
                        concept_understanding="sound",
                        error_type="none",
                        recommended_action="advance",
                        next_difficulty_change="increase",
                        evidence=[f"Content matched MCQ answer '{expected_answer}'"]
                    )
                else:
                    return EvaluationResult(
                        correctness="incorrect",
                        confidence=1.0,
                        concept_understanding="shaky",
                        error_type="conceptual",
                        recommended_action="remediate",
                        next_difficulty_change="decrease",
                        evidence=[f"Selected option '{user_answer}', expected '{expected_answer}'"]
                    )

            # -- 2. Numeric Evaluator (with Tolerance & Unit Checks) --
            if question_type == "numeric":
                # Extract numeric value
                num_match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', text)
                exp_match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', expected_answer) if expected_answer else None

                if num_match and exp_match:
                    user_val = float(num_match.group())
                    exp_val = float(exp_match.group())

                    allowed_err = max(abs(exp_val * tolerance), tolerance)
                    is_num_correct = abs(user_val - exp_val) <= allowed_err

                    # Check units if required
                    unit_err = False
                    if expected_unit:
                        exp_unit_clean = expected_unit.strip().lower()
                        if exp_unit_clean not in clean_text:
                            unit_err = True

                    if is_num_correct and not unit_err:
                        return EvaluationResult(
                            correctness="correct",
                            confidence=0.95,
                            concept_understanding="sound",
                            error_type="none",
                            recommended_action="advance",
                            next_difficulty_change="increase",
                            evidence=[f"Numeric value {user_val} within tolerance of {exp_val}"]
                        )
                    elif is_num_correct and unit_err:
                        return EvaluationResult(
                            correctness="partially_correct",
                            confidence=0.7,
                            concept_understanding="shaky",
                            error_type="unit_error",
                            recommended_action="reinforce",
                            next_difficulty_change="maintain",
                            evidence=[f"Numeric value {user_val} correct, but unit missing or wrong (expected {expected_unit})"]
                        )
                    else:
                        return EvaluationResult(
                            correctness="incorrect",
                            confidence=0.9,
                            concept_understanding="shaky",
                            error_type="arithmetic",
                            recommended_action="remediate",
                            next_difficulty_change="decrease",
                            evidence=[f"Numeric value {user_val} outside allowed tolerance of {exp_val}"]
                        )

            # -- 3. Formula / Reaction Evaluator --
            if question_type in ("formula", "reaction") and expected_answer:
                norm_user = re.sub(r'[\s_]', '', clean_text)
                norm_exp = re.sub(r'[\s_]', '', expected_answer.strip().lower())

                if norm_user == norm_exp:
                    return EvaluationResult(
                        correctness="correct",
                        confidence=0.95,
                        concept_understanding="sound",
                        error_type="none",
                        recommended_action="advance",
                        next_difficulty_change="increase",
                        evidence=[f"Formula/reaction '{user_answer}' matches expected '{expected_answer}'"]
                    )
                else:
                    return EvaluationResult(
                        correctness="incorrect",
                        confidence=0.85,
                        concept_understanding="shaky",
                        error_type="reaction" if question_type == "reaction" else "notation",
                        recommended_action="remediate",
                        next_difficulty_change="decrease",
                        evidence=[f"Formula/reaction '{user_answer}' differs from expected '{expected_answer}'"]
                    )

            # -- 4. Short Answer & Conceptual Evaluator --
            if expected_answer or rubric:
                target = (expected_answer + " " + rubric).lower()
                key_terms = [w for w in re.findall(r'\w{4,}', target) if w not in ("what", "that", "this", "from", "with", "have")]

                matches = [w for w in key_terms if w in clean_text]
                match_ratio = len(matches) / max(len(key_terms), 1)

                if match_ratio >= 0.5:
                    return EvaluationResult(
                        correctness="correct",
                        confidence=0.85,
                        concept_understanding="sound",
                        error_type="none",
                        recommended_action="advance",
                        next_difficulty_change="increase",
                        evidence=[f"Key concepts matched: {matches[:3]}"]
                    )
                elif match_ratio >= 0.2:
                    return EvaluationResult(
                        correctness="partially_correct",
                        confidence=0.6,
                        concept_understanding="shaky",
                        error_type="conceptual",
                        recommended_action="reinforce",
                        next_difficulty_change="maintain",
                        evidence=[f"Partial concept match: {matches}"]
                    )
                else:
                    return EvaluationResult(
                        correctness="incorrect",
                        confidence=0.75,
                        concept_understanding="misconception",
                        error_type="conceptual",
                        recommended_action="remediate",
                        next_difficulty_change="decrease",
                        evidence=[f"Key concepts missing from response: {key_terms[:3]}"]
                    )

            # Default fallback when no answer key is present: check for substantive chemistry discourse
            chem_keywords = {"energy", "heat", "work", "enthalpy", "entropy", "gibbs", "system", "surroundings", "element", "bond", "atom", "reaction", "mole", "pressure", "temperature", "periodic", "acid", "base", "oxidation"}
            found_keywords = [w for w in chem_keywords if w in clean_text]

            if len(clean_text) >= 15 and len(found_keywords) >= 1:
                return EvaluationResult(
                    correctness="correct",
                    confidence=0.8,
                    concept_understanding="sound",
                    error_type="none",
                    recommended_action="proceed",
                    next_difficulty_change="increase",
                    evidence=[f"Substantive response containing relevant chemistry domain concepts: {found_keywords}"]
                )
            else:
                # P2-T04: Ambiguous or brief response defaults to 'uncertain' (NEVER 'incorrect')
                return EvaluationResult(
                    correctness="uncertain",
                    confidence=0.0,
                    concept_understanding="unknown",
                    error_type="other",
                    recommended_action="reinforce",
                    next_difficulty_change="maintain",
                    evidence=["Response insufficiently structured or missing context to verify correctness"]
                )

        except Exception as exc:
            logger.error(f"StudentAnswerEvaluator: evaluation failed unexpectedly: {exc}")
            # P2-T04: Failure defaults to 'uncertain'
            return EvaluationResult(
                correctness="uncertain",
                confidence=0.0,
                concept_understanding="unknown",
                error_type="other",
                recommended_action="reinforce",
                next_difficulty_change="maintain",
                evidence=[f"Evaluation pipeline exception: {exc}"]
            )
