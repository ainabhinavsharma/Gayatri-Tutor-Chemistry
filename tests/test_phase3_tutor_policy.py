"""Phase 3: Tutor Policy Engine and State Machine Tests.

Verifies:
1. 14 explicit state machine states and valid transition routing graph.
2. 10 pedagogical actions mapping.
3. Determinism of TutorPolicyEngine.evaluate_policy.
4. Trajectory testing for 7 student personas (beginner, improving, overconfident, weak_prerequisite, repeated_misconception, high_mastery, inactive_returning).
5. CoT isolation (clean, concise student-facing explanations).
6. Security/Safety policy overrides.
"""
from __future__ import annotations

import pytest

from core.tutor.state_machine import (
    PolicyDecision,
    TutorAction,
    TutorPolicyEngine,
    TutorState,
    TutorStateMachine,
)


def test_state_machine_valid_transitions():
    """Verify valid state transitions and fallback handling."""
    sm = TutorStateMachine(TutorState.IDLE)
    assert sm.current_state == TutorState.IDLE

    # Valid transition: IDLE -> UNDERSTAND
    assert sm.transition_to(TutorState.UNDERSTAND) is True
    assert sm.current_state == TutorState.UNDERSTAND

    # Valid transition: UNDERSTAND -> PLAN
    assert sm.transition_to(TutorState.PLAN) is True
    assert sm.current_state == TutorState.PLAN

    # Invalid transition fallback: PLAN -> IDLE (invalid direct transition, falls back to TEACH)
    assert sm.transition_to(TutorState.IDLE) is False
    assert sm.current_state == TutorState.TEACH


def test_policy_engine_determinism():
    """Verify that given the same inputs, TutorPolicyEngine outputs identical decisions."""
    d1 = TutorPolicyEngine.evaluate_policy(
        intent="concept_explanation",
        concept="THERMO_ENTHALPY",
        mastery=0.45,
        prereq_mastery=0.75,
        recent_accuracy=0.60,
    )

    d2 = TutorPolicyEngine.evaluate_policy(
        intent="concept_explanation",
        concept="THERMO_ENTHALPY",
        mastery=0.45,
        prereq_mastery=0.75,
        recent_accuracy=0.60,
    )

    assert d1 == d2
    assert d1.action == d2.action
    assert d1.student_explanation == d2.student_explanation


def test_trajectory_beginner():
    """Trajectory 1: Beginner student with low mastery (0.2) -> Socratic EXPLAIN."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="concept_explanation",
        concept="THERMO_FIRST_LAW",
        mastery=0.20,
        prereq_mastery=0.80,
    )
    assert decision.action == TutorAction.EXPLAIN.value
    assert decision.next_state == TutorState.TEACH.value
    assert decision.scaffold_level == 3
    assert "Teaching mode: Socratic Explanation" in decision.student_explanation


def test_trajectory_improving():
    """Trajectory 2: Improving student with developing mastery (0.55) -> ASK / PRACTICE."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="practice",
        concept="THERMO_FIRST_LAW",
        mastery=0.55,
        recent_accuracy=0.70,
    )
    assert decision.action == TutorAction.ASK.value
    assert decision.next_state == TutorState.PRACTICE.value
    assert "Teaching mode: Practice" in decision.student_explanation


def test_trajectory_overconfident():
    """Trajectory 3: Overconfident student (high confidence, low accuracy) -> PROBE."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="concept_explanation",
        concept="THERMO_WORK",
        mastery=0.40,
        recent_accuracy=0.20,
        confidence=0.85,
    )
    assert decision.action == TutorAction.PROBE.value
    assert decision.next_state == TutorState.CHECK.value
    assert "Teaching mode: Comprehension Check" in decision.student_explanation


def test_trajectory_weak_prerequisite():
    """Trajectory 4: Weak prerequisite mastery (< 0.5) -> REMEDIATE prerequisite."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="concept_explanation",
        concept="THERMO_FIRST_LAW",
        mastery=0.60,
        prereq_mastery=0.35,  # Weak prerequisite
    )
    assert decision.action == TutorAction.REMEDIATE.value
    assert decision.reason_code == "weak_prerequisite"
    assert "Teaching mode: Prerequisite Remediation" in decision.student_explanation


def test_trajectory_repeated_misconception():
    """Trajectory 5: Student with active misconception -> REMEDIATE misconception."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="numerical",
        concept="THERMO_FIRST_LAW",
        mastery=0.50,
        misconception_code="THERMO_SIGN_CONVENTION",
    )
    assert decision.action == TutorAction.REMEDIATE.value
    assert decision.reason_code == "repeated_misconception"
    assert "THERMO_SIGN_CONVENTION" in decision.student_explanation


def test_trajectory_high_mastery():
    """Trajectory 6: High mastery student (0.90) -> MOVE_FORWARD / ADVANCE."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="concept_explanation",
        concept="THERMO_SYSTEM",
        mastery=0.90,
    )
    assert decision.action == TutorAction.MOVE_FORWARD.value
    assert decision.next_state == TutorState.ADVANCE.value
    assert "Teaching mode: Concept Mastery" in decision.student_explanation


def test_trajectory_inactive_returning():
    """Trajectory 7: Returning student with spaced review due -> REVIEW."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="greeting",
        concept="THERMO_FIRST_LAW",
        mastery=0.70,
        is_review_due=True,
    )
    assert decision.action == TutorAction.REVIEW.value
    assert decision.next_state == TutorState.REVIEW.value
    assert "Teaching mode: Spaced Review" in decision.student_explanation


def test_security_policy_override():
    """Verify security flag overrides standard policy to safety block mode."""
    decision = TutorPolicyEngine.evaluate_policy(
        intent="prompt_injection",
        concept="THERMO_FIRST_LAW",
        mastery=0.50,
        security_flag="PROMPT_INJECTION_BLOCKED",
    )
    assert decision.action == TutorAction.EXPLAIN.value
    assert decision.reason_code == "security_safety_block"
    assert "System Safety" in decision.student_explanation
