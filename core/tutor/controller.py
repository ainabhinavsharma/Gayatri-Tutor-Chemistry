"""Gayatri AI — Core Tutor Controller & The 6 Tutoring Modes (Phases 3 & 4).

Implements:
1. Exactly the 6 MVP Tutor Modes (Section 13):
   - EXPLAIN (Section 14)
   - QUESTION (Section 15)
   - HINT (Section 16: 5-level hint progression)
   - EVALUATE (Section 17)
   - REMEDIATE (Section 18)
   - SUMMARY (Section 19)
2. Coordinated orchestration:
   - RAG Knowledge grounding
   - Adaptive routing and prerequisite traversal
   - Structured JSON prompt contracts for Qwen2.5-3B
   - Telemetry event logging for all actions
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.providers.local import LocalProvider
from core.rag.store import RAGStore
from core.tutor.adaptive import (
    AdaptiveLearningEngine,
    EventLogger,
    StudentProfile,
)
from core.tutor.evaluator import StudentAnswerEvaluator

logger = logging.getLogger("gayatri.tutor.controller")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TutorMode(str, Enum):
    """The 6 Core MVP Tutoring Modes specified in Section 13."""
    EXPLAIN = "EXPLAIN"
    QUESTION = "QUESTION"
    HINT = "HINT"
    EVALUATE = "EVALUATE"
    REMEDIATE = "REMEDIATE"
    SUMMARY = "SUMMARY"


@dataclass
class TutorResponse:
    """Structured response returned by TutorController."""
    mode: TutorMode
    concept_id: str
    text: str
    mastery: float
    mastery_delta: float = 0.0
    hint_level: int = 0
    evaluation_result: Optional[str] = None
    misconception: Optional[str] = None
    retrieved_chunks: List[str] = field(default_factory=list)
    next_recommended_action: str = ""
    event_id: str = ""
    debug_info: Dict[str, Any] = field(default_factory=dict)


class TutorController:
    """Central pedagogical controller implementing the 6 MVP Tutoring Modes."""

    def __init__(
        self,
        student: StudentProfile | None = None,
        event_logger: EventLogger | None = None,
        rag_store: RAGStore | None = None,
    ):
        self.student = student or StudentProfile.load_from_file()
        self.event_logger = event_logger or EventLogger()
        self.rag_store = rag_store or RAGStore()
        self.current_mode = TutorMode(self.student.current_mode) if self.student.current_mode in TutorMode.__members__ else TutorMode.EXPLAIN
        self._load_graph_prerequisites()

    def _load_graph_prerequisites(self) -> None:
        """Load concept graph dependencies from learning_graph/prerequisites.json."""
        self.prerequisites: Dict[str, List[str]] = {}
        p_path = PROJECT_ROOT / "PRIVATE_WORK" / "learning_graph" / "prerequisites.json"
        if p_path.exists():
            try:
                with open(p_path, encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("dependencies", []):
                    self.prerequisites[item["concept_id"]] = item.get("prerequisites", [])
            except Exception as exc:
                logger.warning(f"Could not load prerequisites: {exc}")

    def get_prerequisites(self, concept_id: str) -> List[str]:
        return self.prerequisites.get(concept_id, [])

    # ── Retrieval Helper ────────────────────────────────────────────────

    def retrieve_grounding(self, concept_id: str, query: str = "") -> Tuple[str, List[str]]:
        """Retrieve relevant knowledge chunks from RAG store."""
        search_query = f"{concept_id} {query}".strip()
        matches = self.rag_store.search_similar(search_query, top_k=3)
        if not matches:
            # Fallback to search by concept_id directly
            matches = self.rag_store.search_similar(concept_id, top_k=2)

        evidence_texts = []
        chunk_ids = []
        for chk, score in matches:
            chunk_ids.append(chk.chunk_id)
            evidence_texts.append(f"[{chk.topic} — {chk.subtopic}]\n{chk.text}")

        evidence_block = "\n\n---\n\n".join(evidence_texts)
        return evidence_block, chunk_ids

    # ── Mode 1: EXPLAIN ─────────────────────────────────────────────────

    def handle_explain(self, concept_id: str, user_query: str = "") -> TutorResponse:
        """Section 14: Progressive Socratic Explanation.
        Flow: Concept -> Prior knowledge -> Intuition -> Example -> Definition -> Formula -> Quick check.
        """
        self.current_mode = TutorMode.EXPLAIN
        self.student.current_mode = TutorMode.EXPLAIN.value
        self.student.current_concept = concept_id
        self.student.active_hint_level = 0

        evidence, chunk_ids = self.retrieve_grounding(concept_id, user_query or "explain")

        system_prompt = (
            "You are Gayatri, an expert chemistry tutor teaching high school chemistry.\n"
            "You teach using progressive guided Socratic explanation.\n"
            "Do NOT dump a large textbook paragraph.\n"
            "Structure your response strictly into:\n"
            "1. Core Intuition & Everyday Analogy\n"
            "2. Formal Definition & Formula\n"
            "3. Worked Example / Practical Demonstration\n"
            "4. Quick Check Question to verify student understanding.\n\n"
            f"Ground your answer strictly in this verified curriculum evidence:\n{evidence}"
        )

        user_msg = f"Please explain the concept: {concept_id}. {user_query}".strip()
        raw_output = LocalProvider.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ], max_tokens=600, temperature=0.2)

        mastery = self.student.get_mastery(concept_id)

        # Log event
        evt = self.event_logger.log_event(
            event_type="EXPLANATION_GENERATED",
            student_id=self.student.student_id,
            concept_id=concept_id,
            details={
                "mode": "EXPLAIN",
                "retrieved_chunks": chunk_ids,
                "current_mastery": mastery,
            }
        )
        self.student.save_to_file()

        return TutorResponse(
            mode=TutorMode.EXPLAIN,
            concept_id=concept_id,
            text=raw_output.strip(),
            mastery=mastery,
            retrieved_chunks=chunk_ids,
            next_recommended_action="QUESTION",
            event_id=evt["timestamp"],
            debug_info={"chunks_count": len(chunk_ids), "model": "Qwen2.5-3B-Instruct"}
        )

    # ── Mode 2: QUESTION ────────────────────────────────────────────────

    def handle_question(self, concept_id: str, difficulty: str = "medium") -> TutorResponse:
        """Section 15: Present a single targeted question calibrated to student difficulty."""
        self.current_mode = TutorMode.QUESTION
        self.student.current_mode = TutorMode.QUESTION.value
        self.student.current_concept = concept_id
        self.student.active_hint_level = 0

        evidence, chunk_ids = self.retrieve_grounding(concept_id, "questions practice")

        system_prompt = (
            "You are Gayatri Chemistry Tutor. Your task is to present ONE single targeted question to test student understanding.\n"
            "Rules:\n"
            "- Ask exactly ONE question.\n"
            f"- Calibrate difficulty to: {difficulty}.\n"
            "- Do NOT reveal the answer, explanation, or solution.\n"
            "- Clearly prompt the student to submit their answer.\n\n"
            f"Ground your question in this curriculum evidence:\n{evidence}"
        )

        user_msg = f"Generate a {difficulty} chemistry question testing understanding of {concept_id}."
        raw_output = LocalProvider.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ], max_tokens=300, temperature=0.3)

        mastery = self.student.get_mastery(concept_id)

        evt = self.event_logger.log_event(
            event_type="QUESTION_PRESENTED",
            student_id=self.student.student_id,
            concept_id=concept_id,
            details={"mode": "QUESTION", "difficulty": difficulty, "mastery": mastery}
        )
        self.student.save_to_file()

        return TutorResponse(
            mode=TutorMode.QUESTION,
            concept_id=concept_id,
            text=raw_output.strip(),
            mastery=mastery,
            retrieved_chunks=chunk_ids,
            next_recommended_action="EVALUATE",
            event_id=evt["timestamp"],
            debug_info={"difficulty": difficulty, "active_concept": concept_id}
        )

    # ── Mode 3: HINT (5-Tier Ladder) ────────────────────────────────────

    def handle_hint(
        self,
        concept_id: str,
        question: str = "",
        student_attempt: str = "",
        hint_level: Optional[int] = None,
    ) -> TutorResponse:
        """Section 16: Multi-tier hint progression without immediately revealing answers.
        Ladder:
        Level 1 = Conceptual direction
        Level 2 = Identify relevant principle
        Level 3 = Identify formula / relationship
        Level 4 = Partial setup
        Level 5 = Near-solution
        Then -> REMEDIATE
        """
        self.current_mode = TutorMode.HINT
        self.student.current_mode = TutorMode.HINT.value
        if hint_level is not None:
            self.student.active_hint_level = hint_level
        else:
            self.student.active_hint_level += 1
        level = min(5, self.student.active_hint_level)

        evidence, chunk_ids = self.retrieve_grounding(concept_id, "hints misconceptions")

        tier_instructions = {
            1: "Provide a gentle conceptual direction or broad guiding question (Tier 1 Hint). Do NOT mention any formula or specific numbers.",
            2: "Identify the relevant scientific principle, thermodynamic law, or chemical rule that applies here (Tier 2 Hint).",
            3: "Identify the exact mathematical formula or structural relationship required to solve the problem (Tier 3 Hint).",
            4: "Provide the partial algebraic setup or substitution steps, leaving only the final calculation to the student (Tier 4 Hint).",
            5: "Provide a near-solution hint with the almost-complete reasoning, asking the student for the final step (Tier 5 Hint).",
        }

        directive = tier_instructions.get(level, tier_instructions[1])
        system_prompt = (
            "You are Gayatri Chemistry Tutor giving a pedagogical hint.\n"
            f"Current Hint Tier: Level {level} of 5.\n"
            f"Directive: {directive}\n"
            "Rules:\n"
            "- Do NOT give away the final answer.\n"
            "- Encourage the student to try again.\n\n"
            f"Verified Evidence:\n{evidence}"
        )

        user_msg = (
            f"Concept: {concept_id}\n"
            f"Question: {question}\n"
            f"Student's Previous Attempt: {student_attempt}\n"
            f"Please give a Level {level} hint."
        )

        raw_output = LocalProvider.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ], max_tokens=350, temperature=0.2)

        mastery = self.student.get_mastery(concept_id)

        evt = self.event_logger.log_event(
            event_type="HINT_GIVEN",
            student_id=self.student.student_id,
            concept_id=concept_id,
            details={"mode": "HINT", "hint_level": level, "mastery": mastery}
        )
        self.student.save_to_file()

        next_action = "REMEDIATE" if level >= 5 else "EVALUATE"
        return TutorResponse(
            mode=TutorMode.HINT,
            concept_id=concept_id,
            text=raw_output.strip(),
            mastery=mastery,
            hint_level=level,
            retrieved_chunks=chunk_ids,
            next_recommended_action=next_action,
            event_id=evt["timestamp"],
            debug_info={"hint_level": level, "max_level": 5}
        )

    # ── Mode 4: EVALUATE ────────────────────────────────────────────────

    def handle_evaluate(
        self,
        concept_id: str,
        question: str,
        student_answer: str,
        expected_answer: str = "",
        reference_answer: str = "",
    ) -> TutorResponse:
        """Section 17: Answer evaluation, misconception detection & mastery updates."""
        self.current_mode = TutorMode.EVALUATE
        self.student.current_mode = TutorMode.EVALUATE.value
        expected = expected_answer or reference_answer

        evidence, chunk_ids = self.retrieve_grounding(concept_id, f"evaluation {student_answer}")

        # 1. Deterministic evaluation first
        eval_result = StudentAnswerEvaluator.evaluate_dict({
            "concept_id": concept_id,
            "question": question,
            "student_answer": student_answer,
            "expected_answer": expected,
            "question_type": "conceptual",
        })

        correctness = eval_result.correctness.upper()  # CORRECT, PARTIALLY_CORRECT, INCORRECT, UNCERTAIN
        error_type = eval_result.error_type
        misconception = eval_result.misconception

        # 2. If uncertain, verify with local LLM evaluator
        if correctness == "UNCERTAIN" and LocalProvider.is_available():
            eval_prompt = (
                "You are an educational evaluator for Chemistry.\n"
                f"Concept: {concept_id}\n"
                f"Question: {question}\n"
                f"Student Answer: {student_answer}\n"
                f"Evidence:\n{evidence}\n\n"
                "Evaluate the student answer. Respond ONLY with a valid JSON object in this exact schema:\n"
                '{"result": "CORRECT" | "PARTIALLY_CORRECT" | "INCORRECT" | "UNCLEAR", '
                '"error_type": "SIGN_CONVENTION" | "CONCEPTUAL" | "CALCULATION" | "NONE", '
                '"confidence": 0.90, "misconception": "..." or null}'
            )
            try:
                llm_eval = LocalProvider.chat([
                    {"role": "system", "content": "You are a JSON-only educational assessment evaluator."},
                    {"role": "user", "content": eval_prompt},
                ], max_tokens=150, temperature=0.1)

                clean_json = llm_eval.strip().strip("`").replace("json\n", "").strip()
                parsed = json.loads(clean_json)
                correctness = parsed.get("result", correctness).upper()
                error_type = parsed.get("error_type", error_type)
                misconception = parsed.get("misconception", misconception)
            except Exception as e:
                logger.debug(f"LLM evaluator fallback parsing error: {e}")

        # Check repeated misconception
        is_repeated = False
        if misconception:
            if misconception in self.student.misconceptions:
                is_repeated = True
            else:
                self.student.misconceptions.append(misconception)

        # 3. Calculate mastery delta per Section 21
        delta = AdaptiveLearningEngine.evaluate_mastery_delta(
            result=correctness,
            hint_level=self.student.active_hint_level,
            is_repeated_misconception=is_repeated,
        )

        prev_mastery, new_mastery = self.student.update_mastery(concept_id, delta)

        # Determine next action & feedback message
        if correctness == "CORRECT":
            self.student.active_hint_level = 0
            feedback_text = (
                f"Excellent job! Your answer is correct. "
                f"You demonstrated accurate understanding of {concept_id.replace('_', ' ').title()}."
            )
            next_action = "SUMMARY" if new_mastery >= 0.80 else "QUESTION"
        elif correctness == "PARTIALLY_CORRECT":
            feedback_text = (
                f"You are on the right track, but your answer is partially incomplete. "
                f"Let's refine the specific details."
            )
            next_action = "HINT"
        else:
            # INCORRECT
            feedback_text = (
                f"Not quite. Let's examine what happened. "
                + (f"Notice: You may be encountering the common error: {misconception}. " if misconception else "")
                + f"Let's work through a hint before trying again."
            )
            next_action = "REMEDIATE" if (is_repeated or self.student.active_hint_level >= 3) else "HINT"

        # Log events
        evt_name = "ANSWER_EVALUATED"
        self.event_logger.log_event(
            event_type=evt_name,
            student_id=self.student.student_id,
            concept_id=concept_id,
            details={
                "result": correctness,
                "error_type": error_type,
                "misconception": misconception,
                "previous_mastery": prev_mastery,
                "new_mastery": new_mastery,
                "mastery_delta": delta,
                "next_mode": next_action,
            }
        )

        if misconception:
            self.event_logger.log_event(
                event_type="MISCONCEPTION_DETECTED",
                student_id=self.student.student_id,
                concept_id=concept_id,
                details={"misconception": misconception, "repeated": is_repeated}
            )

        self.event_logger.log_event(
            event_type="MASTERY_UPDATED",
            student_id=self.student.student_id,
            concept_id=concept_id,
            details={"previous_mastery": prev_mastery, "new_mastery": new_mastery, "delta": delta}
        )

        self.student.save_to_file()

        return TutorResponse(
            mode=TutorMode.EVALUATE,
            concept_id=concept_id,
            text=feedback_text,
            mastery=new_mastery,
            mastery_delta=delta,
            evaluation_result=correctness,
            misconception=misconception,
            retrieved_chunks=chunk_ids,
            next_recommended_action=next_action,
            event_id=datetime.now().isoformat(),
            debug_info={
                "error_type": error_type,
                "previous_mastery": f"{prev_mastery:.0%}",
                "new_mastery": f"{new_mastery:.0%}",
                "delta": delta,
                "repeated_misconception": is_repeated,
            }
        )

    # ── Mode 5: REMEDIATE ───────────────────────────────────────────────

    def handle_remediate(self, target_concept: str, prerequisite_override: str | None = None) -> TutorResponse:
        """Section 18: Remediation flow traversing back to prerequisite.
        Flow: Detect problem -> Identify prerequisite -> Return to prerequisite -> Explain differently -> Micro-question.
        """
        self.current_mode = TutorMode.REMEDIATE
        self.student.current_mode = TutorMode.REMEDIATE.value

        prereqs = self.get_prerequisites(target_concept)
        if prerequisite_override:
            prereq_concept = prerequisite_override
        elif prereqs:
            # Find the lowest mastery prerequisite
            prereq_concept = min(prereqs, key=lambda p: self.student.get_mastery(p))
        else:
            prereq_concept = target_concept

        prereq_mastery = self.student.get_mastery(prereq_concept)
        evidence, chunk_ids = self.retrieve_grounding(prereq_concept, "remediation foundation")

        system_prompt = (
            "You are Gayatri Chemistry Tutor entering REMEDIATION mode.\n"
            f"The student is struggling with '{target_concept}'.\n"
            f"You have identified a prerequisite gap in: '{prereq_concept}' (Mastery: {prereq_mastery:.0%}).\n\n"
            "Instructions:\n"
            "1. State gently that before continuing with the target concept, you are returning to review the foundational prerequisite.\n"
            "2. Explain the prerequisite concept simply with an intuitive analogy.\n"
            "3. Present ONE simple micro-question on this prerequisite to test recovery.\n\n"
            f"Curriculum Evidence:\n{evidence}"
        )

        user_msg = f"Remediate foundational gap: target '{target_concept}', prerequisite '{prereq_concept}'."
        raw_output = LocalProvider.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ], max_tokens=500, temperature=0.2)

        evt = self.event_logger.log_event(
            event_type="REMEDIATION_STARTED",
            student_id=self.student.student_id,
            concept_id=target_concept,
            details={
                "prerequisite_concept": prereq_concept,
                "prerequisite_mastery": prereq_mastery,
                "mode": "REMEDIATE",
            }
        )
        self.student.save_to_file()

        return TutorResponse(
            mode=TutorMode.REMEDIATE,
            concept_id=prereq_concept,
            text=raw_output.strip(),
            mastery=prereq_mastery,
            retrieved_chunks=chunk_ids,
            next_recommended_action="EVALUATE",
            event_id=evt["timestamp"],
            debug_info={
                "original_concept": target_concept,
                "remediated_prerequisite": prereq_concept,
                "prerequisite_mastery": f"{prereq_mastery:.0%}",
            }
        )

    # ── Mode 6: SUMMARY ─────────────────────────────────────────────────

    def handle_summary(self, concept_id: str) -> TutorResponse:
        """Section 19: Comprehensive end-of-lesson review report."""
        self.current_mode = TutorMode.SUMMARY
        self.student.current_mode = TutorMode.SUMMARY.value

        mastery = self.student.get_mastery(concept_id)
        prereqs = self.get_prerequisites(concept_id)

        # Build clean summary
        summary_text = (
            f"### 📋 Lesson Summary: {concept_id.replace('_', ' ').title()}\n\n"
            f"- **Final Concept Mastery:** {mastery:.0%}\n"
            f"- **Active Strengths:** Grounded conceptual understanding of core principles\n"
            f"- **Reviewed Misconceptions:** {', '.join(self.student.misconceptions) if self.student.misconceptions else 'None detected'}\n"
            f"- **Next Recommended Concept:** "
            + (f"{prereqs[0].replace('_', ' ').title()}" if prereqs else "Next syllabus topic")
            + "\n\n"
            f"Great effort during this session! Would you like to practice another question or advance to the next topic?"
        )

        evt = self.event_logger.log_event(
            event_type="SESSION_ENDED",
            student_id=self.student.student_id,
            concept_id=concept_id,
            details={"final_mastery": mastery, "misconceptions": self.student.misconceptions}
        )
        self.student.save_to_file()

        return TutorResponse(
            mode=TutorMode.SUMMARY,
            concept_id=concept_id,
            text=summary_text,
            mastery=mastery,
            next_recommended_action="EXPLAIN",
            event_id=evt["timestamp"],
            debug_info={"status": "LESSON_COMPLETE", "final_mastery": f"{mastery:.0%}"}
        )
