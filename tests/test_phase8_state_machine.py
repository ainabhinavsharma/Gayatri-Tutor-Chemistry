"""Phase 8 Test Suite: Tutor State Machine Integration.

Verifies state machine transitions, adaptive state routing, and hint suppression (P8-T01 through P8-T04).
"""
import pytest
from core.tutor.state_machine import TutorState, TutorStateMachine


def test_tutor_state_machine_flow():
    sm = TutorStateMachine(TutorState.IDLE)
    assert sm.current_state == TutorState.IDLE

    # IDLE -> DISCOVERING
    assert sm.transition_to(TutorState.DISCOVERING) is True
    assert sm.current_state == TutorState.DISCOVERING

    # DISCOVERING -> EXPLAINING
    assert sm.transition_to(TutorState.EXPLAINING) is True

    # EXPLAINING -> EXAMPLE
    assert sm.transition_to(TutorState.EXAMPLE) is True

    # EXAMPLE -> CHECKING
    assert sm.transition_to(TutorState.CHECKING) is True

    # CHECKING -> EVALUATING
    assert sm.transition_to(TutorState.EVALUATING) is True


def test_adaptive_state_routing():
    sm = TutorStateMachine(TutorState.EVALUATING)

    # Incorrect with misconception -> REMEDIATING
    next_st = sm.evaluate_next_state(correctness="incorrect", mastery=0.3, misconception_code="HESS_LAW_DIRECTION")
    assert next_st == TutorState.REMEDIATING

    # Correct with high mastery -> COMPLETED
    sm.transition_to(TutorState.EVALUATING)
    next_st = sm.evaluate_next_state(correctness="correct", mastery=0.90)
    assert next_st == TutorState.COMPLETED


def test_hint_suppression():
    sm_learning = TutorStateMachine(TutorState.PRACTICING)
    assert sm_learning.is_hint_allowed() is True

    sm_assess = TutorStateMachine(TutorState.ASSESSING)
    assert sm_assess.is_hint_allowed() is False
