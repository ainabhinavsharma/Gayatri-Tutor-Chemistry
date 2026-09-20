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
    """Structured evaluation metadata for a student answer (Section 12 / Phase 6)."""
    correctness: str  # "correct", "partially_correct", "incorrect", "uncertain"
    confidence: float  # 0.0 to 1.0
    error_type: str = "none"  # "none", "conceptual", "arithmetic", "formula", "unit", "reaction", "notation", "other"
    misconception: Optional[str] = None
    recommended_action: str = "advance"  # "advance", "reinforce", "remediate", "prerequisite_review"
    concept_understanding: str = "sound"  # backward compat: "sound", "shaky", "misconception", "unknown"
    difficulty_delta: float = 0.0
    evidence: List[str] = field(default_factory=list)
    next_difficulty_change: str = "maintain"  # legacy compat

    def to_dict(self) -> dict:
        return {
            "correctness": self.correctness,
            "confidence": round(self.confidence, 2),
            "error_type": self.error_type,
            "misconception": self.misconception,
            "recommended_action": self.recommended_action,
            "concept_understanding": self.concept_understanding,
            "difficulty_delta": self.difficulty_delta,
            "evidence": self.evidence,
            "next_difficulty_change": self.next_difficulty_change,
        }


class StudentAnswerEvaluator:
    """Context-aware, evidence-driven student answer evaluator (Phase 6 / Section 12)."""

    @classmethod
    def evaluate_dict(cls, data: dict) -> EvaluationResult:
        """Evaluate student answer from a dictionary input contract matching Section 12 schema."""
        question_id = str(data.get("question_id") or "").strip()
        concept_id = str(data.get("concept_id") or "").strip()
        question = str(data.get("question") or "").strip()
        student_ans = str(data.get("student_answer") or data.get("user_answer") or "").strip()
        expected_ans = str(data.get("expected_answer") or data.get("answer") or "").strip()
        qtype = str(data.get("question_type") or data.get("type") or "conceptual").strip()
        rubric = str(data.get("rubric") or "").strip()
        tol = float(data.get("tolerance", 0.05))
        exp_unit = str(data.get("expected_unit") or "").strip()

        return cls.evaluate(
            user_answer=student_ans,
            expected_answer=expected_ans,
            question_type=qtype,
            rubric=rubric,
            tolerance=tol,
            expected_unit=exp_unit,
            concept_id=concept_id,
            question_id=question_id,
            question=question,
        )

    @staticmethod
    def evaluate(
        user_answer: str = "",
        expected_answer: str = "",
        question_type: str = "conceptual",
        rubric: str = "",
        tolerance: float = 0.05,
        expected_unit: str = "",
        concept_id: str = "",
        question_id: str = "",
        question: str = "",
        student_answer: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate student answer using structured criteria & evidence (Section 12)."""
        try:
            raw_text = student_answer if student_answer is not None else user_answer
            text = str(raw_text or "").strip()
            clean_text = text.lower()
            qtype = question_type.strip().lower() if question_type else "conceptual"

            if not clean_text:
                return EvaluationResult(
                    correctness="uncertain",
                    confidence=0.0,
                    concept_understanding="unknown",
                    error_type="other",
                    recommended_action="reinforce",
                    evidence=["Empty answer submitted"]
                )

            # Section 12: Generic single-word / number answers alone CANNOT establish correctness
            is_ambiguous_word = clean_text in GENERIC_AMBIGUOUS_WORDS or (clean_text.isdigit() and qtype != "numeric")
            if is_ambiguous_word:
                if not expected_answer and not rubric:
                    return EvaluationResult(
                        correctness="uncertain",
                        confidence=0.0,
                        concept_understanding="unknown",
                        error_type="other",
                        recommended_action="reinforce",
                        next_difficulty_change="maintain",
                        evidence=[f"Ambiguous or generic answer '{text}' provided without question context"]
                    )
                elif qtype in ("conceptual", "explanation", "short_answer", "formula", "reaction"):
                    # Generic single words (yes, correct, 400, 0, etc.) cannot prove non-numeric/conceptual questions correct
                    is_uncertain_word = clean_text in ("yes", "ok", "sure", "idk", "dunno", "maybe")
                    return EvaluationResult(
                        correctness="uncertain" if is_uncertain_word else "incorrect",
                        confidence=0.0 if is_uncertain_word else 0.8,
                        concept_understanding="unknown" if is_uncertain_word else "shaky",
                        error_type="other" if is_uncertain_word else "conceptual",
                        recommended_action="reinforce" if is_uncertain_word else "remediate",
                        next_difficulty_change="maintain" if is_uncertain_word else "decrease",
                        evidence=[f"Single word/number '{text}' cannot establish correctness for a {qtype} question"]
                    )

            # -- 1. MCQ Evaluator --
            if qtype == "mcq" and expected_answer:
                exp_clean = expected_answer.strip().lower()
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
                        evidence=[f"Selected correct option '{text}' matching '{expected_answer}'"]
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
                        evidence=[f"Selected option '{text}', expected '{expected_answer}'"]
                    )

            # -- 2. Numeric Evaluator (with Tolerance & Unit Checks) --
            if qtype == "numeric":
                num_match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', text)
                exp_match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', expected_answer) if expected_answer else None

                if num_match and exp_match:
                    user_val = float(num_match.group())
                    exp_val = float(exp_match.group())

                    allowed_err = max(abs(exp_val * tolerance), tolerance)
                    is_num_correct = abs(user_val - exp_val) <= allowed_err

                    # Check units if specified or extractable from expected_answer
                    req_unit = expected_unit.strip().lower()
                    if not req_unit and expected_answer:
                        unit_sub = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s*([a-zA-Z/°]+(?:\^[0-9-]+)?)', expected_answer)
                        if unit_sub and unit_sub.group(1).strip():
                            req_unit = unit_sub.group(1).strip().lower()

                    unit_err = False
                    if req_unit:
                        if req_unit not in clean_text:
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
                            error_type="unit",
                            recommended_action="reinforce",
                            next_difficulty_change="maintain",
                            evidence=[f"Numeric value {user_val} correct, but unit missing or wrong (expected {req_unit})"]
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
                elif not exp_match and not rubric:
                    return EvaluationResult(
                        correctness="uncertain",
                        confidence=0.0,
                        concept_understanding="unknown",
                        error_type="other",
                        recommended_action="reinforce",
                        next_difficulty_change="maintain",
                        evidence=[f"Numeric answer '{text}' provided without expected answer reference"]
                    )

            # -- 3. Formula / Reaction Evaluator --
            if qtype in ("formula", "reaction") and expected_answer:
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
                        evidence=[f"Formula/reaction '{text}' matches expected '{expected_answer}'"]
                    )
                else:
                    return EvaluationResult(
                        correctness="incorrect",
                        confidence=0.85,
                        concept_understanding="shaky",
                        error_type="reaction" if qtype == "reaction" else "formula",
                        recommended_action="remediate",
                        next_difficulty_change="decrease",
                        evidence=[f"Formula/reaction '{text}' differs from expected '{expected_answer}'"]
                    )

            # -- 4. Short Answer & Conceptual / Explanation Evaluator --
            if expected_answer or rubric:
                target = (expected_answer + " " + rubric).lower()
                key_terms = [w for w in re.findall(r'[a-zA-Z]{4,}', target) if w not in ("what", "that", "this", "from", "with", "have", "when", "does")]

                matches = [w for w in key_terms if w in clean_text]
                match_ratio = len(matches) / max(len(key_terms), 1)

                if match_ratio >= 0.5:
                    return EvaluationResult(
                        correctness="correct",
                        confidence=0.85,
                        concept_understanding="sound",
                        error_type="none",
                        misconception=None,
                        recommended_action="advance",
                        next_difficulty_change="increase",
                        evidence=[f"Key concepts matched: {matches[:3]}"]
                    )

                # Check for known chemistry misconceptions when answer is partial or incorrect
                misconception = None
                try:
                    from core.learning.misconceptions import MisconceptionTracker
                    misconception = MisconceptionTracker.identify_misconception_from_error(
                        concept_id=concept_id,
                        student_answer=text,
                        error_type="conceptual",
                    )
                except Exception as m_exc:
                    logger.debug(f"Misconception lookup error: {m_exc}")

                if match_ratio >= 0.2 and not misconception:
                    return EvaluationResult(
                        correctness="partially_correct",
                        confidence=0.6,
                        concept_understanding="shaky",
                        error_type="conceptual",
                        misconception=None,
                        recommended_action="reinforce",
                        next_difficulty_change="maintain",
                        evidence=[f"Partial concept match: {matches}"]
                    )
                else:
                    return EvaluationResult(
                        correctness="incorrect",
                        confidence=0.75,
                        concept_understanding="misconception" if misconception else "shaky",
                        error_type="conceptual",
                        misconception=misconception,
                        recommended_action="remediate",
                        next_difficulty_change="decrease",
                        evidence=[f"Conceptual mismatch or misconception: {misconception or 'missing key concepts'}"]
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
                    recommended_action="advance",
                    next_difficulty_change="increase",
                    evidence=[f"Substantive response containing relevant chemistry domain concepts: {found_keywords}"]
                )
            else:
                # Ambiguous or brief response defaults to 'uncertain' (NEVER 'incorrect' without key)
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
            # Section 12: Evaluation failure becomes uncertain
            return EvaluationResult(
                correctness="uncertain",
                confidence=0.0,
                concept_understanding="unknown",
                error_type="other",
                misconception=None,
                recommended_action="reinforce",
                next_difficulty_change="maintain",
                evidence=[f"Evaluation pipeline exception: {exc}"]
            )
