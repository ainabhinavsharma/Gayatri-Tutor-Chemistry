"""Gayatri AI — Tutor State Machine.

Defines explicit tutoring lifecycle states and valid state transitions.
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
    TutorState.EXPLAINING: {TutorState.EXAMPLE, TutorState.CHECKING, TutorState.EVALUATING},
    TutorState.EXAMPLE: {TutorState.CHECKING, TutorState.EVALUATING, TutorState.PRACTICING},
    TutorState.CHECKING: {TutorState.EVALUATING, TutorState.EXPLAINING},
    TutorState.EVALUATING: {TutorState.REMEDIATING, TutorState.PRACTICING, TutorState.COMPLETED, TutorState.EXPLAINING},
    TutorState.REMEDIATING: {TutorState.EXPLAINING, TutorState.EXAMPLE, TutorState.CHECKING},
    TutorState.PRACTICING: {TutorState.CHECKING, TutorState.EVALUATING, TutorState.COMPLETED, TutorState.IDLE},
    TutorState.ASSESSING: {TutorState.EVALUATING, TutorState.COMPLETED, TutorState.IDLE},
    TutorState.COMPLETED: {TutorState.IDLE, TutorState.DISCOVERING, TutorState.EXPLAINING, TutorState.PRACTICING},
}


class TutorStateMachine:
    """Manages explicit tutor state transitions for a session."""

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
