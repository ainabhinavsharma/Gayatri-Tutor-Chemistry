"""Tests for Phase 8: Adaptive Learning Engine (Section 14).

Verifies the 6 core components:
1. Difficulty levels (1 Recall, 2 Basic, 3 Standard, 4 Multi-step, 5 Advanced)
2. Adaptive difficulty policy:
   - independent success → increase
   - hint-supported success → maintain
   - partial → maintain/reduce
   - conceptual error → reduce
   - repeated conceptual error → prerequisite remediation
3. Concept selector multi-factor ranking:
   - prerequisite readiness
   - mastery gap
   - review urgency
   - misconception risk
   - curriculum importance
4. Mastery calculation is evidence-driven and not solely reliant on LLM confidence strings.
"""
from datetime import datetime, timedelta
import pytest

from core.learning.policy import DifficultyPolicy, DifficultyDecision, DIFFICULTY_LEVELS, get_difficulty_label
from core.learning.selector import ConceptSelector, ConceptSelectionResult
from core.learning.mastery import MasteryCalculator
from core.learning.misconceptions import MisconceptionTracker
from core.learning.scheduler import SpacedReviewScheduler
from core.learning.progress import ProgressService
from core.tutor.state import TutorStateManager, LearningEvent


def test_difficulty_levels_and_labels():
    """Verify the 5 defined difficulty levels and their labels."""
    assert DIFFICULTY_LEVELS[1] == "Recall"
    assert DIFFICULTY_LEVELS[2] == "Basic"
    assert DIFFICULTY_LEVELS[3] == "Standard"
    assert DIFFICULTY_LEVELS[4] == "Multi-step"
    assert DIFFICULTY_LEVELS[5] == "Advanced"

    assert get_difficulty_label(1) == "Recall"
    assert get_difficulty_label(2) == "Basic"
    assert get_difficulty_label(3) == "Standard"
    assert get_difficulty_label(4) == "Multi-step"
    assert get_difficulty_label(5) == "Advanced"

    # Bounds clamping
    assert get_difficulty_label(0) == "Recall"
    assert get_difficulty_label(6) == "Advanced"


def test_adaptive_policy_independent_success_increases():
    """Rule: independent success (2 consecutive) → increase difficulty (+1)."""
    policy = DifficultyPolicy()

    # 1 independent success -> maintains
    events_1 = [
        LearningEvent(event_id="e1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="correct", hint_used=0),
    ]
    dec_1 = policy.evaluate_next_difficulty(events_1, current_difficulty=2)
    assert dec_1.new_difficulty == 2
    assert dec_1.action == "maintain"

    # 2 consecutive independent successes -> increases
    events_2 = [
        LearningEvent(event_id="e1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="correct", hint_used=0),
        LearningEvent(event_id="e2", student_id="s1", session_id="sess", turn_id="t2",
                      concept_id="c1", correctness="correct", hint_used=0),
    ]
    dec_2 = policy.evaluate_next_difficulty(events_2, current_difficulty=2)
    assert dec_2.new_difficulty == 3
    assert dec_2.action == "increase"
    assert dec_2.difficulty_label == "Standard"

    # Max level 5 cannot increase beyond 5
    dec_max = policy.evaluate_next_difficulty(events_2, current_difficulty=5)
    assert dec_max.new_difficulty == 5
    assert dec_max.action == "maintain"


def test_adaptive_policy_hint_supported_success_maintains():
    """Rule: hint-supported success → maintain current difficulty."""
    policy = DifficultyPolicy()

    events = [
        LearningEvent(event_id="e1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="correct", hint_used=1),
    ]
    decision = policy.evaluate_next_difficulty(events, current_difficulty=3)
    assert decision.new_difficulty == 3
    assert decision.action == "maintain"
    assert "hint" in decision.reason.lower()


def test_adaptive_policy_partial_maintains_or_reduces():
    """Rule: partial → maintain or reduce."""
    policy = DifficultyPolicy()

    events = [
        LearningEvent(event_id="e1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="partially_correct"),
    ]
    decision = policy.evaluate_next_difficulty(events, current_difficulty=4)
    assert decision.new_difficulty in (3, 4)
    assert decision.action in ("maintain", "reduce")


def test_adaptive_policy_conceptual_error_reduces():
    """Rule: conceptual error → reduce (-1)."""
    policy = DifficultyPolicy()

    events = [
        LearningEvent(event_id="e1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="incorrect"),
    ]
    decision = policy.evaluate_next_difficulty(events, current_difficulty=3)
    assert decision.new_difficulty == 2
    assert decision.action == "reduce"
    assert decision.difficulty_label == "Basic"

    # Level 1 cannot drop below 1
    decision_min = policy.evaluate_next_difficulty(events, current_difficulty=1)
    assert decision_min.new_difficulty == 1
    assert decision_min.action == "reduce"


def test_adaptive_policy_repeated_conceptual_error_triggers_prerequisite_review():
    """Rule: repeated conceptual error (2 consecutive) → prerequisite remediation."""
    policy = DifficultyPolicy()

    events = [
        LearningEvent(event_id="e1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="incorrect"),
        LearningEvent(event_id="e2", student_id="s1", session_id="sess", turn_id="t2",
                      concept_id="c1", correctness="incorrect"),
    ]
    decision = policy.evaluate_next_difficulty(events, current_difficulty=3)
    assert decision.new_difficulty == 2
    assert decision.action == "prerequisite_review"
    assert decision.recommend_prerequisite_review is True
    assert "prerequisite" in decision.reason.lower()


def test_concept_selector_multi_factor_ranking(tmp_path):
    """Verify ConceptSelector considers: prerequisite readiness, mastery gap, review urgency, misconception risk."""
    db_path = str(tmp_path / "test_selector.db")
    sm = TutorStateManager(db_path)
    selector = ConceptSelector()

    # Student 1:
    # 1. Prerequisite readiness:
    # chem_thermo_first_law requires chem_thermo_system.
    # Without mastery in chem_thermo_system, chem_thermo_first_law readiness should be 0.2
    score_unready = selector.evaluate_concept_score("student_test", "chem_thermo_first_law", sm)
    assert score_unready["prereq_readiness"] == 0.2

    # Give student mastery in chem_thermo_system
    event_sys = LearningEvent(
        event_id="e_sys_1", student_id="student_test", session_id="sess", turn_id="t1",
        concept_id="chem_thermo_system", correctness="correct"
    )
    # Record multiple events to achieve >= 0.7 mastery
    for i in range(8):
        sm.record_learning_event(LearningEvent(
            event_id=f"e_sys_{i}", student_id="student_test", session_id="sess", turn_id=f"t{i}",
            concept_id="chem_thermo_system", correctness="correct"
        ))

    score_ready = selector.evaluate_concept_score("student_test", "chem_thermo_first_law", sm)
    assert score_ready["prereq_readiness"] == 1.0

    # 2. Mastery gap:
    # A concept with 0.0 mastery has mastery_gap = 1.0
    # A concept with 0.9 mastery has mastery_gap = 0.1
    assert score_ready["mastery_gap"] == 1.0

    # 3. Review urgency:
    # Set next_review_at in the past
    past_due = (datetime.now() - timedelta(days=2)).isoformat()
    sm.conn.execute(
        "UPDATE student_concept_mastery SET next_review_at = ? WHERE student_id = ? AND concept_id = ?",
        (past_due, "student_test", "chem_thermo_system")
    )
    score_overdue = selector.evaluate_concept_score("student_test", "chem_thermo_system", sm)
    assert score_overdue["review_urgency"] == 2.0

    # 4. Misconception risk:
    # Record an active misconception for chem_thermo_first_law
    tracker = MisconceptionTracker(sm)
    tracker.record_misconception("student_test", "chem_thermo_first_law", "THERMO_SIGN_CONVENTION")
    score_misc = selector.evaluate_concept_score("student_test", "chem_thermo_first_law", sm)
    assert score_misc["misconception_risk"] == 1.5


def test_mastery_calculation_is_evidence_driven(tmp_path):
    """Rule 8 / Section 14: Mastery is computed deterministically from evidence, not raw LLM confidence."""
    calc = MasteryCalculator()

    # All correct independent answers
    events_good = [
        LearningEvent(event_id=f"eg_{i}", student_id="s1", session_id="sess", turn_id=f"t{i}",
                      concept_id="c1", correctness="correct", hint_used=0, difficulty=3)
        for i in range(5)
    ]
    mastery_good = calc.compute_mastery(events_good)
    assert mastery_good > 0.85

    # Mix of errors and hints
    events_mixed = [
        LearningEvent(event_id="em_1", student_id="s1", session_id="sess", turn_id="t1",
                      concept_id="c1", correctness="incorrect", difficulty=3),
        LearningEvent(event_id="em_2", student_id="s1", session_id="sess", turn_id="t2",
                      concept_id="c1", correctness="correct", hint_used=1, difficulty=2),
        LearningEvent(event_id="em_3", student_id="s1", session_id="sess", turn_id="t3",
                      concept_id="c1", correctness="partially_correct", difficulty=2),
    ]
    mastery_mixed = calc.compute_mastery(events_mixed)
    assert mastery_mixed < mastery_good
    assert 0.0 <= mastery_mixed <= 1.0


def test_all_adaptive_components_exist():
    """Verify all required Section 14 components are importable and instantiate."""
    assert MasteryCalculator is not None
    assert DifficultyPolicy is not None
    assert MisconceptionTracker is not None
    assert ConceptSelector is not None
    assert SpacedReviewScheduler is not None
    assert ProgressService is not None
