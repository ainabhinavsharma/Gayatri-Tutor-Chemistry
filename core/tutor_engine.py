"""Gayatri AI — Tutor engine: context-aware teaching with LDG integration.

This module is NOT a "tutoring system" (prior art US20240135951A1).
It's a teaching strategy layer that provides concept context to agents.
No patented learning methods implemented.
"""

from __future__ import annotations

import copy
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("gayatri.tutor")

class MasteryLevel(str, Enum):
    INTRODUCED = "Introduced"
    PRACTICING = "Practicing"
    PROFICIENT = "Proficient"
    MASTERED = "Mastered"

class RecoveryMode(str, Enum):
    NORMAL = "Normal"
    MISSING_PREREQUISITES = "MissingPrerequisites"
    EMPTY_CURRICULUM = "EmptyCurriculum"

def mastery_level(score: float) -> str:
    if score >= 0.9:
        return MasteryLevel.MASTERED.value
    elif score >= 0.7:
        return MasteryLevel.PROFICIENT.value
    elif score >= 0.4:
        return MasteryLevel.PRACTICING.value
    return MasteryLevel.INTRODUCED.value


@dataclass
class TutorContext:
    """Current teaching state for a session."""
    current_concept_id: str = ""
    current_concept_name: str = ""
    concept_description: str = ""
    subject: str = ""
    mastery: float = 0.3
    waiting_for_answer: bool = False
    last_response_type: str = "explain"  # explain, question, practice, feedback
    last_attempt_correct: bool | None = None
    last_interaction_time: float = 0.0
    last_student_answer: str = ""
    attempts: int = 0
    correct_count: int = 0
    hint_used: bool = False
    time_to_answer_s: float = 0.0
    review_queue: list[str] = field(default_factory=list)
    recovery_mode: bool = False
    recovery_reason: str = ""
    metadata: dict = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Build a context string for the model system prompt."""
        if not self.current_concept_id:
            return ""

        lines = [
            f"Current teaching concept: {self.current_concept_name}",
            f"Description: {self.concept_description}",
            f"Student mastery: {int(self.mastery * 100)}% ({mastery_level(self.mastery)})",
            f"Attempts: {self.attempts}, Correct: {self.correct_count}",
        ]

        if self.recovery_mode:
            lines.append(f"[RECOVERY MODE ACTIVE]: {self.recovery_reason}")
            lines.append("Inform the student why this foundational prerequisite is being reviewed to prepare them for advanced topics.")

        if self.waiting_for_answer:
            lines.append("You just asked a question. Wait for the student's answer before continuing.")
        elif self.last_response_type == "explain":
            lines.append("After explaining, ask a comprehension question to check understanding.")
        elif self.last_response_type == "question":
            lines.append("Evaluate the student's answer. If correct, praise and move on. If wrong, gently correct and re-explain.")

        return "\n".join(lines)


@dataclass
class TutorTurnTransaction:
    """Manages transactional state changes during a tutor turn (Audit #128).

    If a turn fails (e.g. MODEL_UNAVAILABLE, streaming crash, network error),
    all LDG concept updates and TutorContext mutations are rolled back cleanly.
    """
    engine: TutorEngine
    session_id: str
    orig_context: TutorContext
    orig_concept_state: dict | None = None
    committed: bool = False
    rolled_back: bool = False

    def commit(self) -> None:
        """Commit transaction and persist current state to SQLite."""
        if self.rolled_back:
            raise RuntimeError("Cannot commit a rolled-back tutor transaction")
        self.committed = True
        self.engine.save_context(self.session_id)
        logger.debug(f"Tutor transaction committed for session {self.session_id}")

    def rollback(self) -> None:
        """Roll back in-memory and persisted state to the pre-turn snapshot."""
        if self.committed:
            return
        self.rolled_back = True
        with self.engine._lock:
            # 1. Restore TutorContext in-place and in dict
            current_ctx = self.engine.session_contexts.get(self.session_id)
            if current_ctx is not None:
                current_ctx.__dict__.clear()
                current_ctx.__dict__.update(copy.deepcopy(self.orig_context).__dict__)
            else:
                self.engine.session_contexts[self.session_id] = copy.deepcopy(self.orig_context)
            self.engine.save_context(self.session_id)

            # 2. Restore LDG concept state in SQLite if modified
            if self.orig_concept_state and hasattr(self.engine.ldg, "_conn"):
                try:
                    conn = self.engine.ldg._conn()
                    conn.execute(
                        """UPDATE ldg_concepts
                           SET mastery = ?, exposure_count = ?, error_count = ?, last_practiced = ?
                           WHERE id = ?""",
                        (
                            self.orig_concept_state["mastery"],
                            self.orig_concept_state["exposure_count"],
                            self.orig_concept_state["error_count"],
                            self.orig_concept_state["last_practiced"],
                            self.orig_concept_state["id"],
                        ),
                    )
                    conn.commit()
                    conn.close()
                    if hasattr(self.engine.ldg, "clear_cache"):
                        self.engine.ldg.clear_cache()
                except Exception as exc:
                    logger.error(f"Failed to rollback LDG concept in SQLite: {exc}")

            logger.info(f"Tutor turn transaction rolled back for session {self.session_id}")


class TutorEngine:
    """Orchestrates concept selection, progression, and mastery tracking.

    Wraps the Learning Dependency Graph with teaching logic.
    Thread-safe across multiple concurrent sessions.
    """

    def __init__(self, ldg: Any):
        self.ldg = ldg
        self.session_contexts: dict[str, TutorContext] = {}
        self._lock = threading.RLock()

    def get_or_create_context(self, session_id: str) -> TutorContext:
        """Get or create teaching context for a session, restoring from DB if available."""
        with self._lock:
            if session_id not in self.session_contexts:
                try:
                    from core.session import get_session_store
                    stored = get_session_store().load_tutor_context(session_id)
                    if stored is not None:
                        self.session_contexts[session_id] = stored
                        return stored
                except Exception as exc:
                    logger.debug(f"Could not load persisted tutor context: {exc}")
                self.session_contexts[session_id] = TutorContext()
            return self.session_contexts[session_id]

    def save_context(self, session_id: str) -> None:
        """Persist tutor teaching context to database."""
        with self._lock:
            ctx = self.session_contexts.get(session_id)
            if ctx:
                try:
                    from core.session import get_session_store
                    get_session_store().save_tutor_context(session_id, ctx)
                except Exception as exc:
                    logger.warning(f"Failed to persist tutor context for session {session_id}: {exc}")

    def set_context(self, session_id: str, context: TutorContext) -> None:
        """Set teaching context for a session and persist it."""
        with self._lock:
            self.session_contexts[session_id] = context
            self.save_context(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear teaching context for a session."""
        with self._lock:
            self.session_contexts.pop(session_id, None)

    def begin_transaction(self, session_id: str) -> TutorTurnTransaction:
        """Begin a transactional turn, capturing snapshots of tutor context and concept state (Audit #128)."""
        with self._lock:
            ctx = self.get_or_create_context(session_id)
            orig_ctx = copy.deepcopy(ctx)
            orig_concept_state = None
            if ctx.current_concept_id and hasattr(self.ldg, "get_concept"):
                c = self.ldg.get_concept(ctx.current_concept_id)
                if c:
                    orig_concept_state = {
                        "id": c.id,
                        "mastery": c.mastery,
                        "exposure_count": c.exposure_count,
                        "error_count": c.error_count,
                        "last_practiced": c.last_practiced,
                    }
            return TutorTurnTransaction(
                engine=self,
                session_id=session_id,
                orig_context=orig_ctx,
                orig_concept_state=orig_concept_state,
            )

    def get_next_concept_for_session(self, session_id: str) -> Any:
        """Get the next concept to teach, advancing from current if mastered."""
        with self._lock:
            ctx = self.get_or_create_context(session_id)

            from core.tutor.decay import MasteryDecayScheduler
            scheduler = MasteryDecayScheduler(self.ldg, self)
            scheduler.apply_decay_and_queue(session_id)

            current_id = ctx.current_concept_id

            from core.config import LDG_MASTERY_THRESHOLD
            # If no current concept, or current is mastered or missing, get next
            mastery = self.ldg.get_mastery(current_id) if current_id else None
            if not current_id or mastery is None or mastery >= LDG_MASTERY_THRESHOLD:
                # Check review queue first
                next_concept = None
                while ctx.review_queue:
                    review_id = ctx.review_queue.pop(0)
                    review_mastery = self.ldg.get_mastery(review_id)
                    if review_mastery is not None and review_mastery < LDG_MASTERY_THRESHOLD:
                        next_concept = self.ldg.get_concept(review_id)
                        break
                
                if not next_concept:
                    next_concept = self.ldg.get_next_concept(ctx.subject)
                    
                    if next_concept is None:
                        ctx.metadata['recovery_mode'] = RecoveryMode.EMPTY_CURRICULUM.value
                    elif not self.ldg.is_unlocked(next_concept.id):
                        ctx.metadata['recovery_mode'] = RecoveryMode.MISSING_PREREQUISITES.value
                    else:
                        ctx.metadata['recovery_mode'] = RecoveryMode.NORMAL.value
                else:
                    ctx.metadata['recovery_mode'] = RecoveryMode.NORMAL.value
                
                if next_concept:
                    # Advance context
                    ctx.current_concept_id = next_concept.id
                    ctx.current_concept_name = next_concept.name
                    ctx.concept_description = next_concept.description
                    ctx.mastery = self.ldg.get_mastery(next_concept.id) or 0.3
                    ctx.waiting_for_answer = False
                    ctx.last_response_type = "explain"
                    ctx.attempts = 0
                    ctx.correct_count = 0
                    ctx.hint_used = False
                    ctx.time_to_answer_s = 0.0
                    ctx.recovery_mode = getattr(next_concept, "recovery_mode", False)
                    ctx.recovery_reason = getattr(next_concept, "recovery_reason", "")
                    self.save_context(session_id)
                    logger.info(f"Advanced to concept: {next_concept.name} (Recovery: {ctx.metadata.get('recovery_mode')})")
                    return next_concept
                else:
                    return None
            else:
                # Keep current
                ctx.metadata['recovery_mode'] = RecoveryMode.NORMAL.value
                return self.ldg.get_concept(current_id) if current_id else None

    def record_student_response(self, session_id: str, correct: bool | None,
                                confidence: float = 1.0,
                                student_answer: str = "") -> float:
        """Record a student's answer and update mastery."""
        with self._lock:
            ctx = self.get_or_create_context(session_id)
            if not ctx.current_concept_id:
                return 0.0

            now = time.time()
            if ctx.last_interaction_time > 0:
                elapsed = now - ctx.last_interaction_time
                ctx.time_to_answer_s = elapsed
            else:
                ctx.time_to_answer_s = 0.0

            # Audit #36: Check for duplicate identical submission within short window
            clean_answer = student_answer.strip().lower()
            if clean_answer and clean_answer == ctx.last_student_answer.strip().lower():
                if ctx.last_interaction_time > 0 and (now - ctx.last_interaction_time) < 10.0:
                    logger.info(f"Duplicate answer detected within 10s on session {session_id}; skipping re-assessment")
                    return ctx.mastery

            if correct is not None:
                new_mastery = self.ldg.record_attempt(ctx.current_concept_id, correct, confidence)
                ctx.mastery = new_mastery
                ctx.last_attempt_correct = correct
                ctx.attempts += 1
                if correct:
                    ctx.correct_count += 1
                status = "correct" if correct else "incorrect"
                logger.info(
                    f"Student {status} on {ctx.current_concept_name}: "
                    f"mastery={new_mastery:.3f}"
                )
            else:
                new_mastery = ctx.mastery
                logger.info(
                    f"Student response uncertain on {ctx.current_concept_name}: "
                    f"mastery remains {new_mastery:.3f}"
                )

            ctx.last_response_type = "feedback" if ctx.waiting_for_answer else "explain"
            ctx.last_attempt_correct = correct
            ctx.waiting_for_answer = False
            ctx.last_student_answer = student_answer
            ctx.last_interaction_time = now
            self.save_context(session_id)

            return new_mastery

    def set_waiting_for_answer(self, session_id: str) -> None:
        """Mark that the tutor just asked a question and is waiting."""
        with self._lock:
            ctx = self.get_or_create_context(session_id)
            ctx.waiting_for_answer = True
            ctx.last_response_type = "question"
            ctx.last_interaction_time = time.time()
            self.save_context(session_id)

    def is_waiting_for_answer(self, session_id: str, max_age_seconds: float = 1800.0) -> bool:
        """Check if the tutor is waiting for a student answer (with staleness check, Audit #130)."""
        with self._lock:
            ctx = self.get_or_create_context(session_id)
            if not ctx.waiting_for_answer:
                return False
            if ctx.last_interaction_time > 0 and (time.time() - ctx.last_interaction_time) > max_age_seconds:
                logger.info(
                    f"Tutor waiting_for_answer expired for session {session_id} "
                    f"after {max_age_seconds}s staleness window"
                )
                ctx.waiting_for_answer = False
                self.save_context(session_id)
                return False
            return True

    def get_session_summary(self, session_id: str) -> dict:
        """Get a summary of the current teaching session."""
        with self._lock:
            ctx = self.get_or_create_context(session_id)
            stats = self.ldg.get_progress_stats(ctx.subject)
            return {
                "current_concept": ctx.current_concept_name,
                "mastery": f"{int(ctx.mastery * 100)}%",
                "waiting_for_answer": ctx.waiting_for_answer,
                "progress": stats,
            }




# Global tutor engine (lazy-initialized with LDG, protected by lock)
_tutor_lock = threading.Lock()
_tutor_engine: TutorEngine | None = None


def get_tutor_engine(ldg: Any = None) -> TutorEngine:
    """Get the global tutor engine in a thread-safe manner."""
    global _tutor_engine
    if _tutor_engine is None:
        with _tutor_lock:
            if _tutor_engine is None:
                if ldg is None:
                    from core.knowledge_graph import LearningDependencyGraph
                    ldg = LearningDependencyGraph()
                _tutor_engine = TutorEngine(ldg)
    return _tutor_engine


def reset_tutor_engine() -> None:
    """Reset the global tutor engine (primarily for test isolation)."""
    global _tutor_engine
    with _tutor_lock:
        _tutor_engine = None
