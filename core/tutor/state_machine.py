"""Gayatri AI — Tutor State Machine & Policy Engine (Phase 3).

Implements:
1. 14 Explicit Lifecycle States: IDLE, UNDERSTAND, DIAGNOSE, PLAN, RETRIEVE,
   TEACH, CHECK, EVALUATE, ADAPT, REMEDIATE, PRACTICE, REVIEW, CHALLENGE, ADVANCE.
2. 10 Pedagogical Actions: EXPLAIN, PROBE, HINT, ASK, PRACTICE, REMEDIATE,
   REVIEW, CHALLENGE, SUMMARIZE, MOVE_FORWARD.
3. Deterministic Tutor Policy Engine: Maps multidimensional student state & intent
   to explicit pedagogical actions and scaffold levels without CoT leakage.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("gayatri.tutor.state_machine")


class TutorState(str, Enum):
    IDLE = "IDLE"
    UNDERSTAND = "UNDERSTAND"
    DIAGNOSE = "DIAGNOSE"
    PLAN = "PLAN"
    RETRIEVE = "RETRIEVE"
    TEACH = "TEACH"
    CHECK = "CHECK"
    EVALUATE = "EVALUATE"
    ADAPT = "ADAPT"
    REMEDIATE = "REMEDIATE"
    PRACTICE = "PRACTICE"
    REVIEW = "REVIEW"
    CHALLENGE = "CHALLENGE"
    ADVANCE = "ADVANCE"

    # Backward compatibility aliases for legacy states
    DISCOVERING = "UNDERSTAND"
    EXPLAINING = "TEACH"
    EXAMPLE = "TEACH"
    CHECKING = "CHECK"
    EVALUATING = "EVALUATE"
    REMEDIATING = "REMEDIATE"
    PRACTICING = "PRACTICE"
    ASSESSING = "EVALUATE"
    COMPLETED = "ADVANCE"


class TutorAction(str, Enum):
    EXPLAIN = "EXPLAIN"
    PROBE = "PROBE"
    HINT = "HINT"
    ASK = "ASK"
    PRACTICE = "PRACTICE"
    REMEDIATE = "REMEDIATE"
    REVIEW = "REVIEW"
    CHALLENGE = "CHALLENGE"
    SUMMARIZE = "SUMMARIZE"
    MOVE_FORWARD = "MOVE_FORWARD"


@dataclass
class PolicyDecision:
    """Structured deterministic decision payload matching Phase 3 specification."""
    action: str
    reason_code: str
    concept: str
    scaffold_level: int
    next_state: str
    student_explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Valid state transitions graph for state machine enforcement
VALID_STATE_TRANSITIONS: dict[TutorState, set[TutorState]] = {
    TutorState.IDLE: {TutorState.UNDERSTAND, TutorState.PLAN, TutorState.REVIEW},
    TutorState.UNDERSTAND: {TutorState.DIAGNOSE, TutorState.PLAN, TutorState.RETRIEVE},
    TutorState.DIAGNOSE: {TutorState.PLAN, TutorState.REMEDIATE, TutorState.TEACH},
    TutorState.PLAN: {TutorState.RETRIEVE, TutorState.TEACH, TutorState.CHECK, TutorState.PRACTICE, TutorState.REMEDIATE},
    TutorState.RETRIEVE: {TutorState.TEACH, TutorState.CHECK, TutorState.PRACTICE},
    TutorState.TEACH: {TutorState.CHECK, TutorState.PRACTICE, TutorState.EVALUATE},
    TutorState.CHECK: {TutorState.EVALUATE, TutorState.TEACH, TutorState.REMEDIATE},
    TutorState.EVALUATE: {TutorState.ADAPT, TutorState.REMEDIATE, TutorState.PRACTICE},
    TutorState.ADAPT: {TutorState.PRACTICE, TutorState.REMEDIATE, TutorState.CHALLENGE, TutorState.ADVANCE, TutorState.REVIEW},
    TutorState.REMEDIATE: {TutorState.CHECK, TutorState.TEACH, TutorState.PRACTICE},
    TutorState.PRACTICE: {TutorState.CHECK, TutorState.EVALUATE, TutorState.CHALLENGE, TutorState.ADVANCE},
    TutorState.REVIEW: {TutorState.CHECK, TutorState.PRACTICE, TutorState.ADAPT},
    TutorState.CHALLENGE: {TutorState.EVALUATE, TutorState.ADVANCE, TutorState.PRACTICE},
    TutorState.ADVANCE: {TutorState.IDLE, TutorState.UNDERSTAND, TutorState.PLAN},
}


class TutorStateMachine:
    """State machine governing explicit 14-state tutor transitions."""

    def __init__(self, current_state: TutorState = TutorState.IDLE):
        self._state = current_state

    @property
    def current_state(self) -> TutorState:
        return self._state

    def transition_to(self, new_state: TutorState) -> bool:
        """Attempt to transition to a new state. Returns True if valid, False if fallback applied."""
        valid_next_states = VALID_STATE_TRANSITIONS.get(self._state, set())
        if new_state in valid_next_states or new_state == self._state:
            logger.info(f"Tutor State transition: {self._state.value} -> {new_state.value}")
            self._state = new_state
            return True
        else:
            logger.warning(
                f"Invalid Tutor State transition: {self._state.value} -> {new_state.value}. "
                f"Falling back to TEACH."
            )
            self._state = TutorState.TEACH
            return False

    def evaluate_next_state(
        self,
        correctness: str,
        mastery: float,
        misconception_code: str = "",
        is_assessment: bool = False,
    ) -> TutorState:
        """Evidence-driven state transition router."""
        if is_assessment:
            next_st = TutorState.ADVANCE if mastery >= 0.85 else TutorState.EVALUATE
            self.transition_to(next_st)
            return self._state

        if correctness == "incorrect":
            if misconception_code:
                next_st = TutorState.REMEDIATE
            else:
                next_st = TutorState.TEACH
        elif correctness == "partially_correct":
            next_st = TutorState.PRACTICING
        elif correctness == "correct":
            if mastery >= 0.85:
                next_st = TutorState.ADVANCE
            else:
                next_st = TutorState.PRACTICING
        else:  # uncertain
            next_st = TutorState.CHECK

        self.transition_to(next_st)
        return self._state

    def is_hint_allowed(self) -> bool:
        """Check if hints are allowed in current state."""
        return self._state != TutorState.EVALUATE


class TutorPolicyEngine:
    """Deterministic policy engine selecting pedagogical action and scaffold level."""

    @classmethod
    def evaluate_policy(
        cls,
        intent: str,
        concept: str,
        mastery: float,
        prereq_mastery: float = 1.0,
        recent_accuracy: float = 0.5,
        misconception_code: str | None = None,
        is_review_due: bool = False,
        confidence: float = 0.5,
        hint_dependency: float = 0.0,
        security_flag: str | None = None,
    ) -> PolicyDecision:
        """Select next action and generate student-facing explanation deterministically."""
        # 1. Security or Unsafe Request Override
        if security_flag:
            return PolicyDecision(
                action=TutorAction.EXPLAIN.value,
                reason_code="security_safety_block",
                concept=concept,
                scaffold_level=1,
                next_state=TutorState.TEACH.value,
                student_explanation="Teaching mode: System Safety | Focus: Policy Guidelines | Reason: Request restricted under safety guidelines",
            )

        # 2. Spaced Review Due
        if is_review_due:
            return PolicyDecision(
                action=TutorAction.REVIEW.value,
                reason_code="spaced_review_due",
                concept=concept,
                scaffold_level=2,
                next_state=TutorState.REVIEW.value,
                student_explanation=f"Teaching mode: Spaced Review | Focus: {concept} | Reason: Concept is due for retention check",
            )

        # 3. Active Misconception
        if misconception_code:
            return PolicyDecision(
                action=TutorAction.REMEDIATE.value,
                reason_code="repeated_misconception",
                concept=concept,
                scaffold_level=3,
                next_state=TutorState.REMEDIATE.value,
                student_explanation=f"Teaching mode: Remediation | Focus: {concept} | Reason: Recent answers show recurring misconception ({misconception_code})",
            )

        # 4. Prerequisite Deficit
        if prereq_mastery < 0.50:
            return PolicyDecision(
                action=TutorAction.REMEDIATE.value,
                reason_code="weak_prerequisite",
                concept=concept,
                scaffold_level=3,
                next_state=TutorState.REMEDIATE.value,
                student_explanation=f"Teaching mode: Prerequisite Remediation | Focus: {concept} | Reason: Foundational prerequisite mastery ({prereq_mastery:.0%}) below threshold",
            )

        # 5. Overconfident Trajectory (High Confidence, Low Accuracy)
        if confidence > 0.70 and recent_accuracy < 0.40:
            return PolicyDecision(
                action=TutorAction.PROBE.value,
                reason_code="overconfidence_check",
                concept=concept,
                scaffold_level=2,
                next_state=TutorState.CHECK.value,
                student_explanation=f"Teaching mode: Comprehension Check | Focus: {concept} | Reason: Validating understanding with diagnostic probe",
            )

        # 6. Intent-Driven Explicit Actions
        if intent == "hint":
            scaffold = min(3, max(1, int(hint_dependency * 3) + 1))
            return PolicyDecision(
                action=TutorAction.HINT.value,
                reason_code="student_hint_requested",
                concept=concept,
                scaffold_level=scaffold,
                next_state=TutorState.TEACH.value,
                student_explanation=f"Teaching mode: Socratic Hint | Focus: {concept} | Reason: Providing level {scaffold} scaffolded hint",
            )

        if intent in {"practice", "numerical", "mcq", "problem_solving"}:
            if mastery >= 0.85:
                return PolicyDecision(
                    action=TutorAction.CHALLENGE.value,
                    reason_code="high_mastery_challenge",
                    concept=concept,
                    scaffold_level=1,
                    next_state=TutorState.CHALLENGE.value,
                    student_explanation=f"Teaching mode: Advanced Challenge | Focus: {concept} | Reason: High mastery ({mastery:.0%}) qualifies for application challenge",
                )
            return PolicyDecision(
                action=TutorAction.ASK.value,
                reason_code="practice_requested",
                concept=concept,
                scaffold_level=2,
                next_state=TutorState.PRACTICE.value,
                student_explanation=f"Teaching mode: Practice | Focus: {concept} | Reason: Practicing problem solving to build mastery",
            )

        # 7. Mastery-Based Progression Policy
        if mastery >= 0.85:
            return PolicyDecision(
                action=TutorAction.MOVE_FORWARD.value,
                reason_code="mastery_achieved",
                concept=concept,
                scaffold_level=1,
                next_state=TutorState.ADVANCE.value,
                student_explanation=f"Teaching mode: Concept Mastery | Focus: {concept} | Reason: Concept mastered ({mastery:.0%}), ready to advance",
            )

        if mastery < 0.30:
            return PolicyDecision(
                action=TutorAction.EXPLAIN.value,
                reason_code="beginner_foundational_intro",
                concept=concept,
                scaffold_level=3,
                next_state=TutorState.TEACH.value,
                student_explanation=f"Teaching mode: Socratic Explanation | Focus: {concept} | Reason: Introducing foundational principles",
            )

        # Default Practice & Probe
        return PolicyDecision(
            action=TutorAction.PROBE.value,
            reason_code="developing_understanding_check",
            concept=concept,
            scaffold_level=2,
            next_state=TutorState.CHECK.value,
            student_explanation=f"Teaching mode: Comprehension Check | Focus: {concept} | Reason: Checking understanding of developing concept ({mastery:.0%})",
        )
