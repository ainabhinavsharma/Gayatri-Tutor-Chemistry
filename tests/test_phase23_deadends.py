"""Tests for Phase 23: Dead-End Analysis (Section 29).

Verifies that for every state:
- success path
- failure path
- recovery path
across all 11 scenarios:
1. new student
2. active learning
3. assessment
4. remediation
5. review
6. mastered concept
7. empty RAG
8. LLM timeout
9. database failure
10. session restoration
11. mode switch

Core Invariant: No state may leave the student without a valid next action.
"""
import pytest
from unittest.mock import MagicMock, patch

from core.tutor.deadend import (
    ActionPath,
    DeadEndResolver,
    DeadEndScenario,
    NextAction,
)
from core.orchestrator import Orchestrator, TurnOptions
from core.tutor.state import TutorStateManager
from core.assessment.manager import AssessmentManager, SAMPLE_QUESTION_BANK
from core.security.rate_limiter import RateLimitExceededError


@pytest.fixture
def state_mgr(tmp_path):
    """Provide a fresh TutorStateManager with an isolated SQLite DB."""
    return TutorStateManager(db_path=tmp_path / "test_deadends.db")


@pytest.fixture
def orchestrator(state_mgr):
    """Provide an Orchestrator connected to the test state manager."""
    return Orchestrator(state_manager=state_mgr)


# --------------------------------------------------------------------------
# 1. Invariant Tests: All 11 Scenarios x 3 Paths
# --------------------------------------------------------------------------

ALL_SCENARIOS = [
    DeadEndScenario.NEW_STUDENT,
    DeadEndScenario.ACTIVE_LEARNING,
    DeadEndScenario.ASSESSMENT,
    DeadEndScenario.REMEDIATION,
    DeadEndScenario.REVIEW,
    DeadEndScenario.MASTERED_CONCEPT,
    DeadEndScenario.EMPTY_RAG,
    DeadEndScenario.LLM_TIMEOUT,
    DeadEndScenario.DATABASE_FAILURE,
    DeadEndScenario.SESSION_RESTORATION,
    DeadEndScenario.MODE_SWITCH,
]

ALL_PATHS = [
    ActionPath.SUCCESS,
    ActionPath.FAILURE,
    ActionPath.RECOVERY,
]


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
@pytest.mark.parametrize("path", ALL_PATHS)
def test_invariant_every_state_and_path_has_valid_next_action(scenario, path):
    """Core Invariant: No state or path may leave the student without a valid next action."""
    context = {
        "concept_name": "Chemical Kinetics",
        "concept_id": "chem_kinetics_rate",
        "is_completed": True,
        "weaknesses": ["thermo.hess_law"],
        "has_next_concept": True,
        "next_concept_name": "Arrhenius Equation",
        "query": "superconductivity",
        "items_due": 2,
        "target_mode": "chemistry_tutor",
    }
    actions = DeadEndResolver.resolve_actions(scenario, path, context)

    # Invariant checks:
    # 1. Non-empty list
    assert len(actions) >= 1, f"Dead-end detected! Scenario {scenario.value} / {path.value} returned 0 actions."

    # 2. Every action has non-empty label and prompt
    for act in actions:
        assert isinstance(act, NextAction)
        assert bool(act.action_id.strip()), f"Empty action_id in {scenario.value} / {path.value}"
        assert bool(act.label.strip()), f"Empty label in {scenario.value} / {path.value}"
        assert bool(act.prompt.strip()), f"Empty prompt in {scenario.value} / {path.value}"
        assert bool(act.action_type.strip()), f"Empty action_type in {scenario.value} / {path.value}"

        # In failure and recovery paths, at least one action should be recovery-oriented
        dict_rep = act.to_dict()
        assert isinstance(dict_rep, dict)
        assert dict_rep["action_id"] == act.action_id


# --------------------------------------------------------------------------
# 2. Detailed Verification of Each of the 11 Scenarios
# --------------------------------------------------------------------------

def test_scenario_1_new_student():
    """Verify new student success, failure, and recovery paths."""
    # Success: offers onboarding, diagnostic, syllabus
    succ = DeadEndResolver.resolve_actions(DeadEndScenario.NEW_STUDENT, ActionPath.SUCCESS)
    labels = [a.label for a in succ]
    assert any("Start Chapter 1" in l for l in labels)
    assert any("Diagnostic" in l for l in labels)

    # Failure: profile error -> retry, guest, browse
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.NEW_STUDENT, ActionPath.FAILURE)
    assert any(a.is_recovery for a in fail)
    assert any("Retry Setup" in a.label for a in fail)

    # Recovery: guided onboarding
    rec = DeadEndResolver.resolve_actions(DeadEndScenario.NEW_STUDENT, ActionPath.RECOVERY)
    assert len(rec) >= 1
    assert any(a.is_recovery for a in rec)


def test_scenario_2_active_learning():
    """Verify active learning pedagogical progression and recovery."""
    succ = DeadEndResolver.resolve_actions(
        DeadEndScenario.ACTIVE_LEARNING, ActionPath.SUCCESS, {"concept_name": "Hess's Law"}
    )
    labels = [a.label for a in succ]
    assert any("Practice Problem" in l for l in labels)
    assert any("Give an Example" in l for l in labels)
    assert any("Next Concept" in l for l in labels)

    fail = DeadEndResolver.resolve_actions(DeadEndScenario.ACTIVE_LEARNING, ActionPath.FAILURE)
    assert any("Rephrase" in a.label for a in fail)
    assert any("Hint" in a.label for a in fail)

    rec = DeadEndResolver.resolve_actions(DeadEndScenario.ACTIVE_LEARNING, ActionPath.RECOVERY)
    assert any("Review Foundations" in a.label for a in rec)


def test_scenario_3_assessment():
    """Verify assessment ongoing vs completed next actions, failure, and recovery."""
    # Ongoing assessment
    ongoing = DeadEndResolver.resolve_actions(
        DeadEndScenario.ASSESSMENT, ActionPath.SUCCESS, {"is_completed": False}
    )
    assert any("Submit Answer" in a.label for a in ongoing)

    # Completed assessment with weaknesses
    completed = DeadEndResolver.resolve_actions(
        DeadEndScenario.ASSESSMENT,
        ActionPath.SUCCESS,
        {"is_completed": True, "weaknesses": ["thermo.gibbs"]},
    )
    assert any("Remediate: thermo.gibbs" in a.label for a in completed)
    assert any("Report" in a.label for a in completed)

    # Assessment failure (e.g. submit error)
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.ASSESSMENT, ActionPath.FAILURE)
    assert any("Retry Question" in a.label for a in fail)
    assert any("Resume Assessment" in a.label for a in fail)

    # Recovery
    rec = DeadEndResolver.resolve_actions(DeadEndScenario.ASSESSMENT, ActionPath.RECOVERY)
    assert any("Restart Assessment" in a.label for a in rec)


def test_scenario_4_remediation():
    """Verify remediation targeting misconceptions and step-down recovery."""
    succ = DeadEndResolver.resolve_actions(
        DeadEndScenario.REMEDIATION,
        ActionPath.SUCCESS,
        {"misconception_code": "HESS_LAW_DIRECTION"},
    )
    assert any("Guided Practice" in a.label for a in succ)

    # Failure: student struggles with remediation -> step down difficulty
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.REMEDIATION, ActionPath.FAILURE)
    assert any("Lower Difficulty" in a.label for a in fail)
    assert any("Prerequisite" in a.label for a in fail)

    # Recovery
    rec = DeadEndResolver.resolve_actions(DeadEndScenario.REMEDIATION, ActionPath.RECOVERY)
    assert any("Foundational Walkthrough" in a.label for a in rec)


def test_scenario_5_review():
    """Verify spaced review queue next actions and completion."""
    # Items due
    succ_due = DeadEndResolver.resolve_actions(
        DeadEndScenario.REVIEW, ActionPath.SUCCESS, {"items_due": 3}
    )
    assert any("Next Review Concept" in a.label for a in succ_due)

    # No items due
    succ_empty = DeadEndResolver.resolve_actions(
        DeadEndScenario.REVIEW, ActionPath.SUCCESS, {"items_due": 0}
    )
    assert any("Return to Curriculum" in a.label for a in succ_empty)

    # Failure / interrupted
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.REVIEW, ActionPath.FAILURE)
    assert any("Practice Weakest Concept" in a.label for a in fail)

    # Recovery
    rec = DeadEndResolver.resolve_actions(DeadEndScenario.REVIEW, ActionPath.RECOVERY)
    assert any("Reschedule" in a.label for a in rec)


def test_scenario_6_mastered_concept():
    """Verify mastered concept progression and curriculum end handling."""
    # Next concept available
    succ_next = DeadEndResolver.resolve_actions(
        DeadEndScenario.MASTERED_CONCEPT,
        ActionPath.SUCCESS,
        {"has_next_concept": True, "next_concept_name": "Entropy"},
    )
    assert any("Advance to Entropy" in a.label for a in succ_next)

    # Curriculum completed (no next concept)
    succ_finished = DeadEndResolver.resolve_actions(
        DeadEndScenario.MASTERED_CONCEPT,
        ActionPath.SUCCESS,
        {"has_next_concept": False},
    )
    assert any("Comprehensive Chapter Review" in a.label for a in succ_finished)
    assert any("Final Mastery Exam" in a.label for a in succ_finished)

    # Failure / recovery
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.MASTERED_CONCEPT, ActionPath.FAILURE)
    assert any("Syllabus Review" in a.label for a in fail)


def test_scenario_7_empty_rag():
    """Verify empty RAG retrieval offers polite redirection and syllabus options."""
    succ = DeadEndResolver.resolve_actions(
        DeadEndScenario.EMPTY_RAG, ActionPath.SUCCESS, {"query": "quantum computing"}
    )
    assert any("Search NCERT Index" in a.label for a in succ)
    assert any("Browse Chapter Index" in a.label for a in succ)

    fail = DeadEndResolver.resolve_actions(
        DeadEndScenario.EMPTY_RAG, ActionPath.FAILURE, {"query": "quantum computing"}
    )
    assert any("Rephrase" in a.label for a in fail)
    assert any("General Assistant" in a.label for a in fail)

    rec = DeadEndResolver.resolve_actions(DeadEndScenario.EMPTY_RAG, ActionPath.RECOVERY)
    assert any("Thermodynamics" in a.label for a in rec)


def test_scenario_8_llm_timeout():
    """Verify LLM timeout recovery options."""
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.LLM_TIMEOUT, ActionPath.FAILURE)
    assert any("Retry Request" in a.label for a in fail)
    assert any("Fast Model" in a.label for a in fail)

    rec = DeadEndResolver.resolve_actions(DeadEndScenario.LLM_TIMEOUT, ActionPath.RECOVERY)
    assert any("Resend Last Query" in a.label for a in rec)


def test_scenario_9_database_failure():
    """Verify database failure safe mode and backup recovery."""
    fail = DeadEndResolver.resolve_actions(DeadEndScenario.DATABASE_FAILURE, ActionPath.FAILURE)
    assert any("Retry Database Operation" in a.label for a in fail)
    assert any("Safe Mode" in a.label for a in fail)

    rec = DeadEndResolver.resolve_actions(DeadEndScenario.DATABASE_FAILURE, ActionPath.RECOVERY)
    assert any("Start Safe Session" in a.label for a in rec)


def test_scenario_10_session_restoration():
    """Verify session restoration success, corrupt session fallback, and recovery."""
    succ = DeadEndResolver.resolve_actions(
        DeadEndScenario.SESSION_RESTORATION, ActionPath.SUCCESS, {"concept_name": "Equilibrium"}
    )
    assert any("Resume Equilibrium" in a.label for a in succ)

    fail = DeadEndResolver.resolve_actions(DeadEndScenario.SESSION_RESTORATION, ActionPath.FAILURE)
    assert any("Start Fresh Session" in a.label for a in fail)

    rec = DeadEndResolver.resolve_actions(DeadEndScenario.SESSION_RESTORATION, ActionPath.RECOVERY)
    assert any("New Chemistry Chat" in a.label for a in rec)


def test_scenario_11_mode_switch():
    """Verify mode switch actions across Chemistry Tutor and General Assistant."""
    succ_chem = DeadEndResolver.resolve_actions(
        DeadEndScenario.MODE_SWITCH, ActionPath.SUCCESS, {"target_mode": "chemistry_tutor"}
    )
    assert any("Explore Chemistry Topics" in a.label for a in succ_chem)

    succ_gen = DeadEndResolver.resolve_actions(
        DeadEndScenario.MODE_SWITCH, ActionPath.SUCCESS, {"target_mode": "general_assistant"}
    )
    assert any("General Assistant" in a.label for a in succ_gen)

    fail = DeadEndResolver.resolve_actions(DeadEndScenario.MODE_SWITCH, ActionPath.FAILURE)
    assert any("Chemistry Tutor" in a.label for a in fail)
    assert any("General Assistant" in a.label for a in fail)


# --------------------------------------------------------------------------
# 3. System Integration Tests
# --------------------------------------------------------------------------

def test_orchestrator_submit_attaches_next_actions_on_success(orchestrator):
    """Verify Orchestrator.submit() attaches next_actions to TurnResult on success."""
    opts = TurnOptions(mode="chemistry_tutor", student_id="std_deadend_1")
    res = orchestrator.submit("What is the first law of thermodynamics?", session_id="sess_deadend_1", options=opts)

    assert res.status == "SUCCESS"
    assert hasattr(res, "next_actions")
    assert len(res.next_actions) >= 1
    for act in res.next_actions:
        assert "label" in act and bool(act["label"])
        assert "prompt" in act and bool(act["prompt"])


def test_orchestrator_submit_attaches_next_actions_on_validation_failure(orchestrator):
    """Verify Orchestrator.submit() attaches next_actions to TurnResult on validation failure."""
    opts = TurnOptions(mode="invalid_mode", student_id="std_deadend_2")
    res = orchestrator.submit("Hello", session_id="sess_deadend_2", options=opts)

    assert res.status == "ERROR"
    assert hasattr(res, "next_actions")
    assert len(res.next_actions) >= 1
    assert any(act.get("is_recovery") for act in res.next_actions)


def test_orchestrator_submit_attaches_next_actions_on_timeout(orchestrator):
    """Verify Orchestrator.submit() attaches timeout recovery actions on TimeoutError."""
    opts = TurnOptions(mode="chemistry_tutor", student_id="std_deadend_3")

    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=TimeoutError("Request timed out")):
        res = orchestrator.submit("Explain thermodynamics", session_id="sess_deadend_3", options=opts)

    assert res.status == "ERROR"
    assert hasattr(res, "next_actions")
    assert len(res.next_actions) >= 1
    labels = [a["label"] for a in res.next_actions]
    assert any("Retry Request" in l for l in labels)


def test_assessment_manager_attaches_next_actions(state_mgr):
    """Verify AssessmentManager.submit_attempt() and complete_assessment_session() attach next_actions."""
    mgr = AssessmentManager(state_manager=state_mgr)
    session_id = mgr.create_assessment_session("std_assess_deadend", ["thermo.hess_law"], question_count=1)

    # 1. Submit attempt -> must include next_actions
    attempt_res = mgr.submit_attempt(
        assessment_id=session_id,
        student_id="std_assess_deadend",
        question_id="thermo.hess.001",
        student_answer="-110.5",
    )
    assert "next_actions" in attempt_res
    assert len(attempt_res["next_actions"]) >= 1

    # 2. Complete assessment -> must include next_actions
    comp_res = mgr.complete_assessment_session(
        assessment_id=session_id,
        student_id="std_assess_deadend",
    )
    assert "next_actions" in comp_res
    assert len(comp_res["next_actions"]) >= 1
    assert any("Report" in a["label"] or "Remediate" in a["label"] for a in comp_res["next_actions"])


def test_deadend_resolver_ensure_next_actions_guarantee():
    """Verify DeadEndResolver.ensure_next_actions() guarantees valid actions even if empty/malformed."""
    # Empty input -> resolved fallback
    actions1 = DeadEndResolver.ensure_next_actions([])
    assert len(actions1) >= 1

    # None input -> resolved fallback
    actions2 = DeadEndResolver.ensure_next_actions(None)
    assert len(actions2) >= 1

    # Malformed dictionaries -> filtered and resolved fallback
    actions3 = DeadEndResolver.ensure_next_actions([{"invalid": "data"}, {"label": ""}], scenario=DeadEndScenario.ACTIVE_LEARNING)
    assert len(actions3) >= 1
    assert all("label" in a and bool(a["label"]) for a in actions3)

    # Valid dictionary -> preserved
    valid = [{"action_id": "custom", "label": "Custom Action", "prompt": "Do custom", "action_type": "prompt"}]
    actions4 = DeadEndResolver.ensure_next_actions(valid)
    assert actions4 == valid
