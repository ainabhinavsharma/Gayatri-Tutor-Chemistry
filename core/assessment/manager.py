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
                rubric=self.rubric,
                hint=self.hint,
                explanation=self.explanation,
                common_misconceptions=self.common_misconceptions,
                source_id=self.source,
            )
        else:
            return MCQQuestion(
                question_id=self.id,
                topic_id=self.concept_id,
                difficulty=self.difficulty,
                question_text=self.question,
                correct_answer=self.answer,
                rubric=self.rubric,
                hint=self.hint,
                explanation=self.explanation,
                common_misconceptions=self.common_misconceptions,
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
        """Create a new assessment session record (P6-T02) and persist to assessment & assessment_question."""
        from core.security.rate_limiter import get_governor
        get_governor().check_assessment(student_id)

        assessment_id = f"assess_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        # Select matching questions
        matching_q = [q for q in self.questions if q.concept_id in concepts]
        if not matching_q:
            matching_q = self.questions
        selected_ids = [q.id for q in matching_q[:question_count]]

        with self.state_manager.conn:
            # Section 17 required table: assessment
            self.state_manager.conn.execute('''
                INSERT INTO assessment (
                    assessment_id, student_id, concepts_json, question_ids_json,
                    start_time, status, score
                ) VALUES (?, ?, ?, ?, ?, 'IN_PROGRESS', 0.0)
            ''', (
                assessment_id, student_id, json.dumps(concepts),
                json.dumps(selected_ids), now
            ))
            # Legacy table: assessment_sessions
            self.state_manager.conn.execute('''
                INSERT INTO assessment_sessions (
                    assessment_id, student_id, concepts_json, question_ids_json,
                    start_time, status, score
                ) VALUES (?, ?, ?, ?, ?, 'IN_PROGRESS', 0.0)
            ''', (
                assessment_id, student_id, json.dumps(concepts),
                json.dumps(selected_ids), now
            ))

            # Section 17 required table: assessment_question
            for q_id in selected_ids:
                q_item = self.question_map.get(q_id)
                if q_item:
                    self.state_manager.conn.execute('''
                        INSERT OR REPLACE INTO assessment_question (
                            id, assessment_id, question_id, concept_id, difficulty,
                            type, question, answer, rubric, hint, explanation,
                            common_misconceptions, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        f"{assessment_id}_{q_item.id}",
                        assessment_id,
                        q_item.id,
                        q_item.concept_id,
                        q_item.difficulty,
                        q_item.type,
                        q_item.question,
                        str(q_item.answer),
                        q_item.rubric,
                        q_item.hint,
                        q_item.explanation,
                        json.dumps(q_item.common_misconceptions),
                        q_item.source,
                    ))

        return assessment_id

    def submit_attempt(
        self,
        assessment_id: str,
        student_id: str,
        question_id: str,
        student_answer: Any,
    ) -> dict:
        """Grade and record an attempt on a question (P6-T03) in assessment_attempt & assessment_attempts."""
        item = self.question_map.get(question_id)
        if not item:
            raise ValueError(f"Question ID {question_id} not found in question bank.")

        q_schema = item.to_question_schema()
        is_corr, score_frac, feedback = AssessmentGrader.grade_answer(q_schema, student_answer)

        attempt_id = f"att_{uuid.uuid4().hex[:10]}"
        now = datetime.now().isoformat()

        with self.state_manager.conn:
            # Section 17 required table: assessment_attempt
            self.state_manager.conn.execute('''
                INSERT INTO assessment_attempt (
                    attempt_id, assessment_id, student_id, question_id, concept_id,
                    student_answer, is_correct, score_fraction, feedback, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                attempt_id, assessment_id, student_id, question_id, item.concept_id,
                str(student_answer), 1 if is_corr else 0, score_frac, feedback, now
            ))
            # Legacy table: assessment_attempts
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

        from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
        actions = DeadEndResolver.resolve_actions(
            DeadEndScenario.ASSESSMENT,
            ActionPath.SUCCESS,
            {"is_completed": False}
        )

        return {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "is_correct": is_corr,
            "score_fraction": score_frac,
            "feedback": feedback,
            "detected_misconception": detected_misconception,
            "next_actions": [a.to_dict() for a in actions],
        }

    def complete_assessment_session(self, assessment_id: str, student_id: str) -> dict:
        """Finalize assessment session, compute score, persist to score table, and update learner state (P6-T04)."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_attempt WHERE assessment_id = ? AND student_id = ?",
            (assessment_id, student_id)
        )
        attempts = cursor.fetchall()
        if not attempts:
            from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
            actions = DeadEndResolver.resolve_actions(DeadEndScenario.ASSESSMENT, ActionPath.FAILURE)
            return {
                "assessment_id": assessment_id,
                "score": 0.0,
                "status": "NO_ATTEMPTS",
                "next_actions": [a.to_dict() for a in actions],
            }

        total_score = sum(att["score_fraction"] for att in attempts)
        max_possible = len(attempts)
        score_percentage = round((total_score / max_possible) * 100, 2) if max_possible > 0 else 0.0

        now = datetime.now().isoformat()

        concept_scores: Dict[str, List[float]] = {}
        for att in attempts:
            cid = att["concept_id"]
            if cid not in concept_scores:
                concept_scores[cid] = []
            concept_scores[cid].append(att["score_fraction"])

        strengths = [cid for cid, scores in concept_scores.items() if (sum(scores) / len(scores)) >= 0.7]
        weaknesses = [cid for cid, scores in concept_scores.items() if (sum(scores) / len(scores)) < 0.7]

        # Update assessment session in DB
        score_id = f"score_{uuid.uuid4().hex[:10]}"
        with self.state_manager.conn:
            # Section 17 required table: assessment
            self.state_manager.conn.execute('''
                UPDATE assessment
                SET end_time = ?, status = 'COMPLETED', score = ?
                WHERE assessment_id = ? AND student_id = ?
            ''', (now, score_percentage, assessment_id, student_id))
            # Legacy table: assessment_sessions
            self.state_manager.conn.execute('''
                UPDATE assessment_sessions
                SET end_time = ?, status = 'COMPLETED', score = ?
                WHERE assessment_id = ? AND student_id = ?
            ''', (now, score_percentage, assessment_id, student_id))
            # Section 17 required table: score
            self.state_manager.conn.execute('''
                INSERT OR REPLACE INTO score (
                    score_id, assessment_id, student_id, total_score, max_possible,
                    score_percentage, strengths_json, weaknesses_json, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                score_id,
                assessment_id,
                student_id,
                total_score,
                float(max_possible),
                score_percentage,
                json.dumps(strengths),
                json.dumps(weaknesses),
                now,
            ))

        # Record learning events to mutate student mastery state (Section 17: outcomes become learning events)
        turn_id, ts = generate_turn_id(student_id=student_id, session_id=assessment_id)

        for att in attempts:
            cid = att["concept_id"]
            is_c = bool(att["is_correct"])
            score_frac = att["score_fraction"]

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

        from core.tutor.deadend import DeadEndResolver, DeadEndScenario, ActionPath
        actions = DeadEndResolver.resolve_actions(
            DeadEndScenario.ASSESSMENT,
            ActionPath.SUCCESS,
            {"is_completed": True, "strengths": strengths, "weaknesses": weaknesses},
        )

        return {
            "assessment_id": assessment_id,
            "student_id": student_id,
            "score_percentage": score_percentage,
            "total_attempts": len(attempts),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "status": "COMPLETED",
            "next_actions": [a.to_dict() for a in actions],
        }

    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        """Fetch assessment session record from assessment table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment WHERE assessment_id = ?",
            (assessment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_assessment_questions(self, assessment_id: str) -> List[dict]:
        """Fetch all questions for an assessment from assessment_question table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_question WHERE assessment_id = ? ORDER BY question_id",
            (assessment_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_assessment_attempts(self, assessment_id: str) -> List[dict]:
        """Fetch all attempts for an assessment from assessment_attempt table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM assessment_attempt WHERE assessment_id = ? ORDER BY submitted_at",
            (assessment_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_assessment_score(self, assessment_id: str) -> Optional[dict]:
        """Fetch score record for an assessment from score table."""
        cursor = self.state_manager.conn.execute(
            "SELECT * FROM score WHERE assessment_id = ?",
            (assessment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
