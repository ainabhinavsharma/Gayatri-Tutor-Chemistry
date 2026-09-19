"""Gayatri AI — Tutor State Machine (Phase 8).

Defines explicit tutoring lifecycle states, valid state transitions,
and adaptive state routing based on evaluation & evidence persistence.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger("gayatri.tutor.state_machine")


class TutorState(str, Enum):
    IDLE = "IDLE"
    DISCOVERING = "DISCOVERING"
    EXPLAINING = "EXPLAINING"
    EXAMPLE = "EXAMPLE"
    CHECKING = "CHECKING"
    EVALUATING = "EVALUATING"
    REMEDIATING = "REMEDIATING"
    PRACTICING = "PRACTICING"
    ASSESSING = "ASSESSING"
    COMPLETED = "COMPLETED"


# Explicit valid transitions dictionary
VALID_TRANSITIONS: dict[TutorState, set[TutorState]] = {
    TutorState.IDLE: {TutorState.DISCOVERING, TutorState.EXPLAINING, TutorState.PRACTICING, TutorState.ASSESSING},
    TutorState.DISCOVERING: {TutorState.EXPLAINING, TutorState.PRACTICING, TutorState.IDLE},
    TutorState.EXPLAINING: {TutorState.EXAMPLE, TutorState.CHECKING, TutorState.EVALUATING, TutorState.PRACTICING, TutorState.COMPLETED},
    TutorState.EXAMPLE: {TutorState.CHECKING, TutorState.EVALUATING, TutorState.PRACTICING},
    TutorState.CHECKING: {TutorState.EVALUATING, TutorState.EXPLAINING, TutorState.REMEDIATING, TutorState.PRACTICING},
    TutorState.EVALUATING: {TutorState.REMEDIATING, TutorState.PRACTICING, TutorState.COMPLETED, TutorState.EXPLAINING, TutorState.CHECKING},
    TutorState.REMEDIATING: {TutorState.EXPLAINING, TutorState.EXAMPLE, TutorState.CHECKING, TutorState.EVALUATING, TutorState.PRACTICING},
    TutorState.PRACTICING: {TutorState.CHECKING, TutorState.EVALUATING, TutorState.COMPLETED, TutorState.IDLE, TutorState.REMEDIATING},
    TutorState.ASSESSING: {TutorState.EVALUATING, TutorState.COMPLETED, TutorState.IDLE},
    TutorState.COMPLETED: {TutorState.IDLE, TutorState.DISCOVERING, TutorState.EXPLAINING, TutorState.PRACTICING},
}


class TutorStateMachine:
    """Manages explicit tutor state transitions and adaptive progression rules for a session."""

    def __init__(self, current_state: TutorState = TutorState.IDLE):
        self._state = current_state

    @property
    def current_state(self) -> TutorState:
        return self._state

    def transition_to(self, new_state: TutorState) -> bool:
        """Attempt to transition to a new state. Returns True if valid, False if illegal."""
        valid_next_states = VALID_TRANSITIONS.get(self._state, set())
        if new_state in valid_next_states or new_state == self._state:
            logger.info(f"Tutor State transition: {self._state.value} -> {new_state.value}")
            self._state = new_state
            return True
        else:
            logger.warning(
                f"Invalid Tutor State transition requested: {self._state.value} -> {new_state.value}. "
                f"Falling back to EXPLAINING."
            )
            self._state = TutorState.EXPLAINING
            return False

    def evaluate_next_state(
        self,
        correctness: str,
        mastery: float,
        misconception_code: str = "",
        is_assessment: bool = False,
    ) -> TutorState:
        """Evidence-driven state router (P8-T01)."""
        if is_assessment:
            next_st = TutorState.COMPLETED if mastery >= 0.85 else TutorState.ASSESSING
            self.transition_to(next_st)
            return self._state

        if correctness == "incorrect":
            if misconception_code:
                next_st = TutorState.REMEDIATING
            else:
                next_st = TutorState.EXPLAINING
        elif correctness == "partially_correct":
            next_st = TutorState.PRACTICING
        elif correctness == "correct":
            if mastery >= 0.85:
                next_st = TutorState.COMPLETED
            else:
                next_st = TutorState.PRACTICING
        else:  # uncertain
            next_st = TutorState.CHECKING

        self.transition_to(next_st)
        return self._state

    def is_hint_allowed(self) -> bool:
        """Assessment mode suppresses unnecessary hints."""
        return self._state != TutorState.ASSESSING
