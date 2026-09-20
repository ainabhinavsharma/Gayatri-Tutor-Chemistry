"""Phase 4 Test Suite: Adaptive Learning Engine.

Verifies evidence-driven mastery calculation, difficulty policy,
misconception tracking, concept selection, and event stream filtering (P4-T01 through P4-T04).
"""
import pytest
import tempfile
from pathlib import Path

from core.learning.mastery import MasteryCalculator, MasteryWeights
from core.learning.policy import DifficultyPolicy, DifficultyDecision
from core.learning.misconceptions import MisconceptionTracker, THERMODYNAMICS_MISCONCEPTIONS
from core.learning.selector import ConceptSelector
from core.learning.events import LearningEventStream
from core.tutor.state import LearningEvent, TutorStateManager, generate_turn_id


@pytest.fixture
def temp_state_manager():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    sm = TutorStateManager(db_path=db_path)
    yield sm
    try:
        Path(db_path).unlink()
    except Exception:
        pass


def test_mastery_calculator_weak_vs_strong():
    calc = MasteryCalculator()

    # Weak student events
    weak_events = [
        LearningEvent(event_id='e1', student_id='s1', session_id='sess1', turn_id='t1', concept_id='c1', correctness='incorrect', difficulty=2.0),
        LearningEvent(event_id='e2', student_id='s1', session_id='sess1', turn_id='t2', concept_id='c1', correctness='incorrect', difficulty=2.0),
        LearningEvent(event_id='e3', student_id='s1', session_id='sess1', turn_id='t3', concept_id='c1', correctness='partially_correct', difficulty=2.0, hint_used=1),
    ]
    weak_mastery = calc.compute_mastery(weak_events)
    assert 0.0 <= weak_mastery < 0.3

    # Strong student events
    strong_events = [
        LearningEvent(event_id='e4', student_id='s2', session_id='sess1', turn_id='t4', concept_id='c1', correctness='correct', difficulty=4.0, hint_used=0),
        LearningEvent(event_id='e5', student_id='s2', session_id='sess1', turn_id='t5', concept_id='c1', correctness='correct', difficulty=5.0, hint_used=0),
        LearningEvent(event_id='e6', student_id='s2', session_id='sess1', turn_id='t6', concept_id='c1', correctness='correct', difficulty=5.0, hint_used=0),
    ]
    strong_mastery = calc.compute_mastery(strong_events)
    assert strong_mastery > 0.7


def test_mastery_calculator_uncertain_ignored():
    calc = MasteryCalculator()
    events = [
        LearningEvent(event_id='e1', student_id='s1', session_id='sess1', turn_id='t1', concept_id='c1', correctness='uncertain', difficulty=3.0),
    ]
    mastery = calc.compute_mastery(events)
    assert mastery == 0.0


def test_learning_event_stream_filters():
    """Phase 4 Re-audit: Verify LearningEventStream event filtering and metrics."""
    events = [
        LearningEvent(event_id='e1', student_id='s1', session_id='sess1', turn_id='t1', concept_id='c1', correctness='correct', hint_used=0),
        LearningEvent(event_id='e2', student_id='s1', session_id='sess1', turn_id='t2', concept_id='c1', correctness='uncertain', hint_used=0),
        LearningEvent(event_id='e3', student_id='s1', session_id='sess1', turn_id='t3', concept_id='c1', correctness='correct', hint_used=1),
        LearningEvent(event_id='e4', student_id='s1', session_id='sess1', turn_id='t4', concept_id='c1', correctness='incorrect', hint_used=0),
    ]

    valid = LearningEventStream.filter_valid_events(events)
    assert len(valid) == 3

    recent_acc = LearningEventStream.calculate_recent_accuracy(events, n=2)
    assert recent_acc == 0.5  # (1.0 + 0.0) / 2

    independent_rate = LearningEventStream.get_independent_success_rate(events)
    assert independent_rate == 0.5  # 1 out of 2 correct answers used no hints


def test_difficulty_policy_rules():
    policy = DifficultyPolicy()

    # Rule: 2 consecutive independent correct -> increase difficulty
    events_correct = [
        LearningEvent(event_id='e1', student_id='s1', session_id='sess1', turn_id='t1', concept_id='c1', correctness='correct', hint_used=0),
        LearningEvent(event_id='e2', student_id='s1', session_id='sess1', turn_id='t2', concept_id='c1', correctness='correct', hint_used=0),
    ]
    decision = policy.evaluate_next_difficulty(events_correct, current_difficulty=3)
    assert decision.new_difficulty == 4
    assert decision.action == 'increase'

    # Rule: Correct with hint -> maintain difficulty
    events_hint = [
        LearningEvent(event_id='e3', student_id='s1', session_id='sess1', turn_id='t3', concept_id='c1', correctness='correct', hint_used=1),
    ]
    decision = policy.evaluate_next_difficulty(events_hint, current_difficulty=3)
    assert decision.new_difficulty == 3
    assert decision.action == 'maintain'

    # Rule: Single conceptual error -> reduce difficulty
    events_error = [
        LearningEvent(event_id='e4', student_id='s1', session_id='sess1', turn_id='t4', concept_id='c1', correctness='incorrect'),
    ]
    decision = policy.evaluate_next_difficulty(events_error, current_difficulty=3)
    assert decision.new_difficulty == 2
    assert decision.action == 'reduce'

    # Rule: 2 consecutive conceptual errors -> trigger prerequisite review
    events_2error = [
        LearningEvent(event_id='e5', student_id='s1', session_id='sess1', turn_id='t5', concept_id='c1', correctness='incorrect'),
        LearningEvent(event_id='e6', student_id='s1', session_id='sess1', turn_id='t6', concept_id='c1', correctness='incorrect'),
    ]
    decision = policy.evaluate_next_difficulty(events_2error, current_difficulty=3)
    assert decision.action == 'prerequisite_review'
    assert decision.recommend_prerequisite_review is True


def test_misconception_tracker_lifecycle(temp_state_manager):
    tracker = MisconceptionTracker(state_manager=temp_state_manager)

    code = 'THERMO_SIGN_CONVENTION'
    # Record misconception for student_A
    rec = tracker.record_misconception('student_A', 'thermo.work', code)
    assert rec.occurrence_count == 1
    assert rec.resolved is False

    # Fetch active misconceptions
    active = tracker.get_active_misconceptions('student_A', 'thermo.work')
    assert len(active) == 1
    assert active[0].misconception_code == code

    # Check student isolation: student_B should have no active misconceptions
    active_B = tracker.get_active_misconceptions('student_B', 'thermo.work')
    assert len(active_B) == 0

    # Resolve misconception
    tracker.resolve_misconception('student_A', 'thermo.work', code)
    active_after = tracker.get_active_misconceptions('student_A', 'thermo.work')
    assert len(active_after) == 0


def test_concept_selector_ranking(temp_state_manager):
    selector = ConceptSelector()

    # Set up student_1 mastery states
    temp_state_manager.conn.execute('''
        INSERT INTO student_concept_mastery (student_id, concept_id, mastery)
        VALUES ('student_1', 'thermo.enthalpy', 0.8), ('student_1', 'thermo.first_law', 0.8)
    ''')

    candidates = ['thermo.hess_law', 'thermo.gibbs']
    result = selector.select_next_concept('student_1', candidates, temp_state_manager)
    assert result.selected_concept_id in candidates
    assert len(result.candidate_rankings) == 2
