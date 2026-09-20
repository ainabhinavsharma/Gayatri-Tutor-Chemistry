"""Tests for Phase 24: Test Hardening (Section 30).

Implements comprehensive test hardening:
1. Property-style invariants:
   - 0 <= mastery <= 1
   - 1 <= difficulty <= 5
   - duplicate event cannot double-count
   - Student A cannot affect Student B
   - invalid curriculum cannot load successfully
2. Permanent regression tests for all P0/P1 bugs & architectural invariants.
3. End-to-end integration test of complete student learning journey.
4. Concurrency & thread-safety stress testing.
"""
import concurrent.futures
import json
import threading
import time
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.curriculum.models import CurriculumManifest
from core.curriculum.validator import CurriculumCorruptionError, CurriculumValidator
from core.curriculum.provider import CurriculumProvider
from core.knowledge_graph import LearningDependencyGraph
from core.learning.mastery import MasteryCalculator, MasteryWeights
from core.learning.misconceptions import MisconceptionTracker
from core.learning.scheduler import SpacedReviewScheduler
from core.mode import AppMode
from core.orchestrator import Orchestrator, TurnOptions
from core.security.cache import IsolatedCacheManager, StudentCacheKey
from core.security.rate_limiter import SlidingWindowRateLimiter, RateLimitExceededError
from core.security.upload import SecureUploadManager
from core.security.validation import validate_concept_id, validate_student_id
from core.tutor.deadend import ActionPath, DeadEndResolver, DeadEndScenario
from core.tutor.difficulty import DifficultyManager
from core.tutor.evaluator import EvaluationResult, StudentAnswerEvaluator
from core.tutor.lifecycle import TurnLifecycleManager, TurnStage
from core.tutor.state import LearningEvent, TutorStateManager, generate_turn_id
from core.tutor_engine import TutorEngine, TutorContext


@pytest.fixture
def state_mgr(tmp_path):
    """Provide a fresh TutorStateManager with an isolated SQLite DB."""
    return TutorStateManager(db_path=tmp_path / "test_hardening.db")


@pytest.fixture
def orchestrator(state_mgr):
    """Provide an Orchestrator connected to the test state manager."""
    return Orchestrator(state_manager=state_mgr)


# ==========================================================================
# 1. Property-Style Invariant Tests
# ==========================================================================

def test_invariant_mastery_bounded_0_to_1():
    """Property Invariant 1: 0 <= mastery <= 1 across all boundary and extreme inputs."""
    calc = MasteryCalculator()

    # Case A: 0 events -> 0.0
    assert calc.compute_mastery([]) == 0.0

    # Case B: 100 consecutive correct events with no hints, max difficulty
    perfect_events = [
        LearningEvent(
            event_id=f"evt_perf_{i}",
            student_id="std_inv_1",
            session_id="sess_1",
            turn_id=f"t_{i}",
            concept_id="thermo.first_law",
            correctness="correct",
            confidence=1.0,
            difficulty=5.0,
            hint_used=0,
            source="review",
        )
        for i in range(100)
    ]
    mastery_perf = calc.compute_mastery(perfect_events)
    assert 0.0 <= mastery_perf <= 1.0
    assert mastery_perf >= 0.95

    # Case C: 100 consecutive incorrect events, min difficulty
    fail_events = [
        LearningEvent(
            event_id=f"evt_fail_{i}",
            student_id="std_inv_1",
            session_id="sess_1",
            turn_id=f"t_{i}",
            concept_id="thermo.first_law",
            correctness="incorrect",
            confidence=0.1,
            difficulty=1.0,
            hint_used=3,
        )
        for i in range(100)
    ]
    mastery_fail = calc.compute_mastery(fail_events)
    assert 0.0 <= mastery_fail <= 1.0
    assert mastery_fail == 0.0

    # Case D: Mixed distribution with partial correctness and hints
    mixed_events = []
    for i in range(50):
        corr = "correct" if i % 3 == 0 else ("partially_correct" if i % 3 == 1 else "incorrect")
        mixed_events.append(
            LearningEvent(
                event_id=f"evt_mix_{i}",
                student_id="std_inv_1",
                session_id="sess_1",
                turn_id=f"t_{i}",
                concept_id="thermo.first_law",
                correctness=corr,
                confidence=0.5,
                difficulty=float((i % 5) + 1),
                hint_used=i % 2,
            )
        )
    mastery_mix = calc.compute_mastery(mixed_events)
    assert 0.0 <= mastery_mix <= 1.0


def test_invariant_difficulty_bounded_1_to_5():
    """Property Invariant 2: 1 <= difficulty <= 5 across any sequence of evaluations."""
    # Start at L1, simulate 10 consecutive correct + high confidence answers
    diff = 1
    eval_corr = EvaluationResult(correctness="correct", confidence=0.95)
    for _ in range(10):
        diff = DifficultyManager.calculate_next_difficulty(diff, eval_corr)
        assert 1 <= diff <= 5
    assert diff == 5  # Reached ceiling

    # From L5, simulate 10 consecutive incorrect answers
    eval_inc = EvaluationResult(correctness="incorrect", confidence=0.8)
    for _ in range(10):
        diff = DifficultyManager.calculate_next_difficulty(diff, eval_inc)
        assert 1 <= diff <= 5
    assert diff == 1  # Reached floor


def test_invariant_duplicate_event_cannot_double_count(state_mgr):
    """Property Invariant 3: duplicate event cannot double-count (idempotent evidence ingestion)."""
    event = LearningEvent(
        event_id="evt_idem_999",
        student_id="std_idem_1",
        session_id="sess_idem_1",
        turn_id="turn_idem_1",
        concept_id="thermo.first_law",
        correctness="correct",
        confidence=0.9,
        difficulty=3.0,
    )

    # First ingestion -> True
    first_res = state_mgr.record_learning_event(event)
    assert first_res is True

    m1 = state_mgr.get_student_concept_mastery("std_idem_1", "thermo.first_law")
    assert m1.exposure_count == 1
    assert m1.correct_count == 1

    # Second ingestion with exact same event_id -> False (rejected)
    second_res = state_mgr.record_learning_event(event)
    assert second_res is False

    # State must NOT double-count
    m2 = state_mgr.get_student_concept_mastery("std_idem_1", "thermo.first_law")
    assert m2.exposure_count == 1
    assert m2.correct_count == 1
    assert m2.mastery == m1.mastery


def test_invariant_student_a_cannot_affect_student_b(state_mgr):
    """Property Invariant 4: Student A cannot affect Student B across all dimensions."""
    # Student A achieves high mastery
    for i in range(5):
        state_mgr.record_learning_event(
            LearningEvent(
                event_id=f"evt_stdA_{i}",
                student_id="student_alpha",
                session_id="sess_A",
                turn_id=f"turn_A_{i}",
                concept_id="thermo.hess_law",
                correctness="correct",
                confidence=1.0,
                difficulty=3.0,
            )
        )

    # Student B has 0 events
    rec_A = state_mgr.get_student_concept_mastery("student_alpha", "thermo.hess_law")
    rec_B = state_mgr.get_student_concept_mastery("student_beta", "thermo.hess_law")

    assert rec_A.exposure_count == 5
    assert rec_A.mastery > 0.4
    assert rec_B.exposure_count == 0
    assert rec_B.mastery == 0.0

    # Cache isolation check
    cache = IsolatedCacheManager()
    key_A = StudentCacheKey(student_id="student_alpha", concept_id="thermo.hess_law", session_id="sess_A", query="What is Hess's law?")
    key_B = StudentCacheKey(student_id="student_beta", concept_id="thermo.hess_law", session_id="sess_B", query="What is Hess's law?")

    cache.set(key_A, {"response": "Secret for A"})
    assert cache.get(key_A) == {"response": "Secret for A"}
    assert cache.get(key_B) is None  # B cannot access A's cache


def test_invariant_invalid_curriculum_cannot_load(tmp_path):
    """Property Invariant 5: invalid curriculum cannot load successfully."""
    # 1. Cyclic curriculum
    cyclic_file = tmp_path / "cyclic_curriculum.json"
    cyclic_data = {
        "subject": "chemistry",
        "concepts": [
            {"id": "c1", "name": "Concept 1", "difficulty": 2, "prerequisites": ["c2"]},
            {"id": "c2", "name": "Concept 2", "difficulty": 3, "prerequisites": ["c1"]},
        ],
    }
    with open(cyclic_file, "w", encoding="utf-8") as f:
        json.dump(cyclic_data, f)

    graph = LearningDependencyGraph(db_path=tmp_path / "ldg_test.db")
    provider = CurriculumProvider(subject="chemistry")
    provider.file_path = cyclic_file

    with pytest.raises(CurriculumCorruptionError) as exc_info:
        provider.load_into(graph)
    assert any("cycle" in err.lower() for err in exc_info.value.errors)
    count = graph._conn().execute("SELECT COUNT(*) FROM ldg_concepts").fetchone()[0]
    assert count == 0

    # 2. Missing prerequisite curriculum
    missing_file = tmp_path / "missing_prereq.json"
    missing_data = {
        "subject": "chemistry",
        "concepts": [
            {"id": "c1", "name": "Concept 1", "difficulty": 2, "prerequisites": ["non_existent"]},
        ],
    }
    with open(missing_file, "w", encoding="utf-8") as f:
        json.dump(missing_data, f)

    provider.file_path = missing_file
    with pytest.raises(CurriculumCorruptionError):
        provider.load_into(graph)
    count2 = graph._conn().execute("SELECT COUNT(*) FROM ldg_concepts").fetchone()[0]
    assert count2 == 0


# ==========================================================================
# 2. Permanent Regression Tests for P0/P1 Bugs
# ==========================================================================

def test_regression_general_assistant_never_mutates_mastery(orchestrator, state_mgr):
    """Regression 1: General Assistant activity != Chemistry learning state."""
    opts = TurnOptions(mode="general_assistant", student_id="std_reg_gen_1")
    res = orchestrator.submit("Write a poem about rain.", session_id="sess_gen_1", options=opts)

    assert res.status == "SUCCESS"
    assert res.agent_name == "general_assistant"

    # Invariant: No learning events or concept mastery records created
    count = state_mgr.conn.execute(
        "SELECT COUNT(*) FROM learning_events WHERE student_id = ?", ("std_reg_gen_1",)
    ).fetchone()[0]
    assert count == 0

    mastery = state_mgr.get_student_concept_mastery("std_reg_gen_1", "thermo.first_law")
    assert mastery.exposure_count == 0
    assert mastery.mastery == 0.0


def test_regression_silent_failure_elimination(orchestrator, state_mgr):
    """Regression 2: Silent failures eliminated — all errors record TURN_ABORTED with sanitized messages."""
    opts = TurnOptions(mode="chemistry_tutor", student_id="std_reg_fail_1")

    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=RuntimeError("Database lock failure")):
        res = orchestrator.submit("Explain thermodynamics", session_id="sess_reg_fail_1", options=opts)

    assert res.status == "ERROR"
    assert "error" in res.routing_reason
    assert "Traceback" not in res.text
    assert "File \"" not in res.text
    assert "I encountered an error" in res.text

    # Turn lifecycle must record TURN_ABORTED
    row = state_mgr.conn.execute(
        "SELECT stage, error_detail FROM turn_lifecycle WHERE student_id = ?", ("std_reg_fail_1",)
    ).fetchone()
    assert row is not None
    assert row["stage"] == TurnStage.TURN_ABORTED.value
    assert "Database lock failure" in row["error_detail"]


def test_regression_cache_isolation_multi_student():
    """Regression 3: Student A cached response != Student B response."""
    cache = IsolatedCacheManager()
    key_A = StudentCacheKey(student_id="std_A", concept_id="chem.kinetics", session_id="sess_A", query="What is rate constant?")
    key_B = StudentCacheKey(student_id="std_B", concept_id="chem.kinetics", session_id="sess_B", query="What is rate constant?")

    cache.set(key_A, {"text": "Response tailored for Student A"})
    assert cache.get(key_A) is not None
    assert cache.get(key_B) is None  # Must NOT hit for Student B


def test_regression_failed_turn_never_records_progress(orchestrator, state_mgr):
    """Regression 4: A failed API turn must never update progress as successful."""
    opts = TurnOptions(mode="chemistry_tutor", student_id="std_reg_prog_1")

    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=TimeoutError("Request timed out")):
        res = orchestrator.submit("Explain Hess's law", session_id="sess_reg_prog_1", options=opts)

    assert res.status == "ERROR"
    rec = state_mgr.get_student_concept_mastery("std_reg_prog_1", "thermo.hess_law")
    assert rec.exposure_count == 0
    assert rec.mastery == 0.0


def test_regression_evaluator_rejects_pure_keyword_matching():
    """Regression 5: Evaluator requires evidence & rubric, rejecting blind keyword matching."""
    # Ambiguous single words alone cannot prove arbitrary questions correct
    res1 = StudentAnswerEvaluator.evaluate(
        user_answer="yes",
        question="Explain Hess's law of constant heat summation.",
        expected_answer="Enthalpy change is independent of the pathway taken.",
        question_type="conceptual",
    )
    assert res1.correctness != "correct"

    res2 = StudentAnswerEvaluator.evaluate(
        user_answer="correct",
        question="Why does entropy increase in spontaneous processes?",
        expected_answer="Spontaneous processes increase total entropy of the universe.",
        question_type="conceptual",
    )
    assert res2.correctness != "correct"


def test_regression_utf8_bom_handling(tmp_path):
    """Regression 6: Ingestion and validation handle UTF-8 BOM without crashing."""
    bom_file = tmp_path / "bom_curriculum.json"
    data = {
        "subject": "chemistry",
        "concepts": [
            {"id": "chem.bom", "name": "BOM Concept", "difficulty": 2, "prerequisites": []},
        ],
    }
    # Write with explicit UTF-8 BOM
    with open(bom_file, "wb") as f:
        f.write(b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8"))

    validator = CurriculumValidator()
    result = validator.validate_curriculum_file(bom_file)
    assert result.is_valid is True
    assert result.concept_count == 1


def test_regression_rate_limiter_empty_deque_safety():
    """Regression 7: Rate limiter handles max_requests=0 / empty deque cleanly without IndexError."""
    limiter = SlidingWindowRateLimiter(max_requests=0, window_s=60)
    assert limiter.is_allowed("std_1") is False

    with pytest.raises(RateLimitExceededError):
        limiter.acquire("std_1")


def test_regression_upload_security_double_extensions(tmp_path):
    """Regression 8: Upload manager strictly blocks executable extensions and double extensions."""
    mgr = SecureUploadManager(base_dir=tmp_path / "uploads")

    # Double extension .exe.pdf
    with pytest.raises(ValueError) as exc1:
        mgr.save_upload("std_1", "malware.exe.pdf", b"%PDF-1.4 valid pdf header")
    assert "Double extension" in str(exc1.value)

    # Script extension .sh
    with pytest.raises(ValueError) as exc2:
        mgr.save_upload("std_1", "script.sh", b"#!/bin/bash\necho hello")
    assert "not permitted" in str(exc2.value).lower() or "extension" in str(exc2.value).lower()


def test_regression_transaction_rollback_clean_state(tmp_path):
    """Regression 9: Turn transaction abort cleanly rolls back state mutations."""
    graph = LearningDependencyGraph(db_path=tmp_path / "ldg_rb.db")
    graph.add_concept("thermo.first_law", "First Law", difficulty=0.5)

    engine = TutorEngine(ldg=graph)
    session_id = "sess_rollback_1"
    ctx = engine.get_or_create_context(session_id)
    ctx.current_concept_id = "thermo.first_law"
    ctx.mastery = 0.3

    txn = engine.begin_transaction(session_id)
    ctx.mastery = 0.9  # Uncommitted mutation

    # Abort / rollback
    txn.rollback()
    restored_ctx = engine.get_or_create_context(session_id)
    assert restored_ctx.mastery == 0.3  # Restored


def test_regression_zero_dead_ends():
    """Regression 10: Zero dead ends — every state and path provides valid next actions."""
    for sc in DeadEndScenario:
        for path in ActionPath:
            actions = DeadEndResolver.resolve_actions(sc, path)
            assert len(actions) >= 1
            for act in actions:
                assert bool(act.label.strip())
                assert bool(act.prompt.strip())


# ==========================================================================
# 3. End-to-End Integration Test
# ==========================================================================

def test_integration_complete_student_learning_journey(orchestrator, state_mgr):
    """Integration: Full student journey from onboarding to mastery."""
    student_id = "std_journey_1"
    session_id = "sess_journey_1"

    # 1. Onboarding / New Student
    new_actions = DeadEndResolver.resolve_actions(DeadEndScenario.NEW_STUDENT, ActionPath.SUCCESS)
    assert len(new_actions) >= 1

    # 2. Active Learning: Student studies First Law of Thermodynamics
    opts = TurnOptions(mode="chemistry_tutor", student_id=student_id)
    res1 = orchestrator.submit("Explain the First Law of Thermodynamics", session_id=session_id, options=opts)
    assert res1.status == "SUCCESS"
    assert len(res1.next_actions) >= 1

    # 3. Student makes an error exhibiting a misconception
    tracker = MisconceptionTracker(state_mgr)
    tracker.record_misconception(student_id, "thermo.hess_law", "HESS_LAW_DIRECTION")
    active_misc = tracker.get_active_misconceptions(student_id)
    assert len(active_misc) >= 1

    # 4. Remediation next actions provided
    remed_actions = DeadEndResolver.resolve_actions(
        DeadEndScenario.REMEDIATION,
        ActionPath.SUCCESS,
        {"misconception_code": "HESS_LAW_DIRECTION"},
    )
    assert any("Guided Practice" in a.label for a in remed_actions)

    # 5. Student resolves misconception with 9 correct learning events to reach >= 0.85 mastery
    for i in range(9):
        state_mgr.record_learning_event(
            LearningEvent(
                event_id=f"evt_journey_{i}",
                student_id=student_id,
                session_id=session_id,
                turn_id=f"turn_j_{i}",
                concept_id="thermo.hess_law",
                correctness="correct",
                confidence=0.95,
                difficulty=3.0,
                hint_used=0,
                source="practice",
            )
        )
    tracker.resolve_misconception(student_id, "thermo.hess_law", "HESS_LAW_DIRECTION")
    assert len(tracker.get_active_misconceptions(student_id)) == 0

    # 6. Spaced Review scheduled and retention delayed recall verified
    scheduler = SpacedReviewScheduler()
    # Simulate that review date has arrived (due in past) to trigger retention verification
    past_due = (datetime.now() - timedelta(days=1)).isoformat()
    state_mgr.conn.execute(
        "UPDATE student_concept_mastery SET next_review_at = ? WHERE student_id = ? AND concept_id = ?",
        (past_due, student_id, "thermo.hess_law")
    )
    sched_res = scheduler.update_schedule_and_check_retention(
        student_id=student_id,
        concept_id="thermo.hess_law",
        correctness="correct",
        hint_used=0,
        state_manager=state_mgr,
    )
    assert sched_res.retention_verified is True
    assert sched_res.interval_days >= 1

    # Post-retention correct turn unlocks mastery >= 0.85
    state_mgr.record_learning_event(
        LearningEvent(
            event_id="evt_journey_retention",
            student_id=student_id,
            session_id=session_id,
            turn_id="turn_j_ret",
            concept_id="thermo.hess_law",
            correctness="correct",
            confidence=1.0,
            difficulty=3.0,
            source="spaced_review",
        )
    )

    # 7. Mastery reached >= 0.85 unlocks next concept
    mastery_rec = state_mgr.get_student_concept_mastery(student_id, "thermo.hess_law")
    assert mastery_rec.mastery >= 0.85
    mastered_actions = DeadEndResolver.resolve_actions(
        DeadEndScenario.MASTERED_CONCEPT,
        ActionPath.SUCCESS,
        {"has_next_concept": True, "next_concept_name": "Entropy"},
    )
    assert any("Advance to Entropy" in a.label for a in mastered_actions)


# ==========================================================================
# 4. Concurrency Stress Test
# ==========================================================================

def test_concurrency_multi_student_stress(state_mgr):
    """Concurrency: 10 concurrent threads simulating multiple students without race conditions."""
    errors = []
    num_threads = 10
    events_per_thread = 10

    def worker(worker_id: int):
        student_id = f"std_concurrent_{worker_id}"
        session_id = f"sess_concurrent_{worker_id}"
        try:
            for i in range(events_per_thread):
                evt = LearningEvent(
                    event_id=f"evt_conc_{worker_id}_{i}",
                    student_id=student_id,
                    session_id=session_id,
                    turn_id=f"turn_conc_{worker_id}_{i}",
                    concept_id="thermo.first_law",
                    correctness="correct" if i % 2 == 0 else "partially_correct",
                    confidence=0.8,
                    difficulty=3.0,
                )
                state_mgr.record_learning_event(evt)
        except Exception as exc:
            errors.append(f"Worker {worker_id} error: {exc}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrency errors encountered: {errors}"

    # Verify each student's exposure count matches exactly
    for i in range(num_threads):
        rec = state_mgr.get_student_concept_mastery(f"std_concurrent_{i}", "thermo.first_law")
        assert rec.exposure_count == events_per_thread
