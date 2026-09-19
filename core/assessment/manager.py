"""Assessment Engine Manager (Phase 6).

Implements question bank schema, assessment session persistence,
attempt recording, grading, score calculation, and student learning state updates.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.assessment.grader import AssessmentGrader
from core.assessment.schema import MCQQuestion, NumericalQuestion, Question, QuestionType
from core.learning.mastery import MasteryCalculator
from core.learning.misconceptions import MisconceptionTracker
from core.tutor.state import LearningEvent, TutorStateManager, generate_turn_id

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


@dataclass
class QuestionBankItem:
    id: str
    concept_id: str
    difficulty: int
    type: str
    question: str
    answer: Any
    rubric: str = ""
    hint: str = ""
    explanation: str = ""
    common_misconceptions: List[str] = field(default_factory=list)
    source: str = "NCERT"

    def to_question_schema(self) -> Question:
        if self.type == "numeric" or self.type == "numerical":
            try:
                val = float(self.answer)
            except ValueError:
                val = 0.0
            return NumericalQuestion(
                question_id=self.id,
                topic_id=self.concept_id,
                difficulty=self.difficulty,
                question_text=self.question,
                expected_value=val,
                explanation=self.explanation,
                source_id=self.source,
            )
        else:
            return MCQQuestion(
                question_id=self.id,
                topic_id=self.concept_id,
                difficulty=self.difficulty,
                question_text=self.question,
                correct_answer=self.answer,
                explanation=self.explanation,
                source_id=self.source,
            )


# Default Sample Question Bank (P6-T01 NCERT Aligned)
SAMPLE_QUESTION_BANK: List[QuestionBankItem] = [
    QuestionBankItem(
        id="thermo.hess.001",
        concept_id="thermo.hess_law",
        difficulty=3,
        type="numeric",
        question="Given C + O2 -> CO2 (delta H = -393.5 kJ/mol) and CO + 1/2 O2 -> CO2 (delta H = -283.0 kJ/mol), calculate delta H for C + 1/2 O2 -> CO.",
        answer="-110.5",
        rubric="Subtract equation 2 from equation 1",
        hint="Invert the second equation and flip the sign of its enthalpy.",
        explanation="delta H = -393.5 - (-283.0) = -110.5 kJ/mol",
        common_misconceptions=["HESS_LAW_DIRECTION", "THERMO_SIGN_CONVENTION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="thermo.gibbs.001",
        concept_id="thermo.gibbs",
        difficulty=2,
        type="mcq",
        question="For a spontaneous reaction at constant temperature and pressure, which condition must hold true?",
        answer="delta G < 0",
        rubric="Gibbs free energy change must be negative for spontaneous processes",
        explanation="A reaction is spontaneous when delta G = delta H - T delta S is less than zero.",
        common_misconceptions=["GIBBS_SIGN_CONFUSION"],
        source="NCERT",
    ),
    QuestionBankItem(
        id="inorganic.periodicity.001",
        concept_id="inorganic.periodicity",
        difficulty=2,
        type="mcq",
        question="Which of the following elements has the highest first ionization enthalpy?",
        answer="Helium",
        rubric="Ionization enthalpy increases across a period and up a group",
        explanation="Helium has a closed-shell 1s2 configuration and smallest atomic radius.",
        common_misconceptions=["PERIODIC_TREND_CONFUSION"],
        source="NCERT",
    ),
]


class AssessmentManager:
    """Manages assessment lifecycle, grading, persistence, and evidence recording."""

    def __init__(self, state_manager: TutorStateManager, questions: Optional[List[QuestionBankItem]] = None):
        self.state_manager = state_manager
        self.questions = questions or SAMPLE_QUESTION_BANK
        self.question_map = {q.id: q for q in self.questions}

    def create_assessment_session(
        self,
        student_id: str,
        concepts: List[str],
        question_count: int = 5,
    ) -> str:
        """Create a new assessment session record (P6-T02)."""
        assessment_id = f"assess_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        # Select matching questions
        matching_q = [q for q in self.questions if q.concept_id in concepts]
        if not matching_q:
            matching_q = self.questions
        selected_ids = [q.id for q in matching_q[:question_count]]

        with self.state_manager.conn:
            self.state_manager.conn.execute('''
                INSERT INTO assessment_sessions (
                    assessment_id, student_id, concepts_json, question_ids_json,
                    start_time, status, score
                ) VALUES (?, ?, ?, ?, ?, 'IN_PROGRESS', 0.0)
            ''', (
                assessment_id, student_id, json.dumps(concepts),
                json.dumps(selected_ids), now
            ))

        return assessment_id

    def submit_attempt(
        self,
        assessment_id: str,
        student_id: str,
        question_id: str,
        student_answer: Any,
    ) -> dict:
        """Grade and record an attempt on a question (P6-T03)."""
        item = self.question_map.get(question_id)
        if not item:
            raise ValueError(f"Question ID {question_id} not found in question bank.")

        q_schema = item.to_question_schema()
        is_corr, score_frac, feedback = AssessmentGrader.grade_answer(q_schema, student_answer)

        attempt_id = f"att_{uuid.uuid4().hex[:10]}"
        now = datetime.now().isoformat()

        with self.state_manager.conn:
            self.state_manager.conn.execute('''
                INSERT INTO assessment_attempts (
                    attempt_id, assessment_id, student_id, question_id, concept_id,
                    student_answer, is_correct, score_fraction, feedback, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt_id, assessment_id, student_id, question_id, item.concept_id,
                str(student_answer), 1 if is_corr else 0, score_frac, feedback, now
            ))

        # Check misconception
        detected_misconception = ""
        if not is_corr and item.common_misconceptions:
            detected_misconception = item.common_misconceptions[0]
            tracker = MisconceptionTracker(self.state_manager)
            tracker.record_misconception(student_id, item.concept_id, detected_misconception)

        return {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "is_correct": is_corr,
            "score_fraction": score_frac,
            "feedback": feedback,
            "detected_misconception": detected_misconception,
        }

    def complete_assessment_session(self, assessment_id: str, student_id: str) -> dict:
        """Finalize assessment session, compute score, and update learner state (P6-T04)."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_attempts WHERE assessment_id = ? AND student_id = ?",
            (assessment_id, student_id)
        )
        attempts = cursor.fetchall()
        if not attempts:
            return {"assessment_id": assessment_id, "score": 0.0, "status": "NO_ATTEMPTS"}

        total_score = sum(att["score_fraction"] for att in attempts)
        max_possible = len(attempts)
        score_percentage = round((total_score / max_possible) * 100, 2) if max_possible > 0 else 0.0

        now = datetime.now().isoformat()

        # Update assessment session in DB
        with self.state_manager.conn:
            self.state_manager.conn.execute('''
                UPDATE assessment_sessions
                SET end_time = ?, status = 'COMPLETED', score = ?
                WHERE assessment_id = ? AND student_id = ?
            ''', (now, score_percentage, assessment_id, student_id))

        # Record learning events to mutate student mastery state
        turn_id, ts = generate_turn_id(student_id=student_id, session_id=assessment_id)
        mastery_calc = MasteryCalculator()

        concept_scores: Dict[str, List[float]] = {}
        misconceptions_detected: List[str] = []

        for att in attempts:
            cid = att["concept_id"]
            is_c = bool(att["is_correct"])
            score_frac = att["score_fraction"]

            if cid not in concept_scores:
                concept_scores[cid] = []
            concept_scores[cid].append(score_frac)

            correctness_str = "correct" if is_c else ("partially_correct" if score_frac > 0 else "incorrect")

            event = LearningEvent(
                event_id=f"evt_{att['attempt_id']}",
                student_id=student_id,
                session_id=assessment_id,
                turn_id=turn_id,
                concept_id=cid,
                question_id=att["question_id"],
                timestamp=ts,
                difficulty=3.0,
                correctness=correctness_str,
                source="assessment",
            )
            self.state_manager.record_learning_event(event)

        strengths = [cid for cid, scores in concept_scores.items() if (sum(scores) / len(scores)) >= 0.7]
        weaknesses = [cid for cid, scores in concept_scores.items() if (sum(scores) / len(scores)) < 0.7]

        return {
            "assessment_id": assessment_id,
            "student_id": student_id,
            "score_percentage": score_percentage,
            "total_attempts": len(attempts),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "status": "COMPLETED",
        }
