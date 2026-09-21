"""Test suite for SQLite concurrency, retry resiliency, and state manager caching."""
import concurrent.futures
import sqlite3
import threading
import pytest
from pathlib import Path

from core.orchestrator import Orchestrator
from core.tutor.lifecycle import TurnLifecycleManager, TurnStage
from core.tutor.state import TutorStateManager, generate_turn_id
from core.db import execute_with_retry, with_db_retry


def test_orchestrator_state_manager_caching(tmp_path: Path):
    """Verify that Orchestrator.get_state_manager() caches the manager thread-safely."""
    db_file = tmp_path / "test_cache.db"
    sm = TutorStateManager(db_path=db_file)
    orch = Orchestrator(state_manager=sm)

    mgr1 = orch.get_state_manager()
    mgr2 = orch.get_state_manager()
    assert mgr1 is mgr2
    assert mgr1 is sm

    # Test lazy initialization caching when initialized with None
    orch_lazy = Orchestrator(state_manager=None)
    lazy_mgr1 = orch_lazy.get_state_manager()
    lazy_mgr2 = orch_lazy.get_state_manager()
    assert lazy_mgr1 is lazy_mgr2
    assert isinstance(lazy_mgr1, TutorStateManager)


def test_turn_lifecycle_rapid_stages(tmp_path: Path):
    """Verify rapid consecutive stage transitions execute smoothly without lock errors."""
    db_file = tmp_path / "test_rapid.db"
    sm = TutorStateManager(db_path=db_file)
    lm = TurnLifecycleManager(sm)

    for i in range(20):
        turn_id, _ = generate_turn_id(student_id="test_student", session_id="test_session")
        rec = lm.start_turn(turn_id, "test_student", "test_session", concept_id="chem_thermo_system")
        assert rec.stage == TurnStage.TURN_STARTED

        lm.update_stage(turn_id, TurnStage.EVALUATION_STARTED)
        lm.update_stage(turn_id, TurnStage.RESPONSE_GENERATED)
        lm.update_stage(turn_id, TurnStage.EVALUATION_COMPLETED)
        lm.update_stage(turn_id, TurnStage.LEARNING_STATE_UPDATED)
        lm.update_stage(turn_id, TurnStage.TURN_COMMITTED)

        # Verify final state in DB
        cursor = sm.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["stage"] == TurnStage.TURN_COMMITTED.value


def test_multithreaded_lifecycle_concurrency(tmp_path: Path):
    """Verify concurrent threads performing turns against the same DB handle retries cleanly."""
    db_file = tmp_path / "test_threaded.db"
    
    # Initialize schema first
    init_sm = TutorStateManager(db_path=db_file)
    del init_sm

    num_threads = 8
    turns_per_thread = 5

    def worker_turn(worker_id: int):
        sm = TutorStateManager(db_path=db_file)
        lm = TurnLifecycleManager(sm)
        for t_idx in range(turns_per_thread):
            turn_id, _ = generate_turn_id(student_id=f"student_{worker_id}", session_id=f"session_{worker_id}")
            lm.start_turn(turn_id, f"student_{worker_id}", f"session_{worker_id}", "concept_test")
            lm.update_stage(turn_id, TurnStage.RESPONSE_GENERATED)
            lm.update_stage(turn_id, TurnStage.TURN_COMMITTED)
        return worker_id

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_turn, i) for i in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == num_threads

    # Verify total committed turns in DB
    verify_sm = TutorStateManager(db_path=db_file)
    cursor = verify_sm.conn.execute(
        "SELECT count(*) FROM turn_lifecycle WHERE stage = ?",
        (TurnStage.TURN_COMMITTED.value,)
    )
    total_committed = cursor.fetchone()[0]
    assert total_committed == num_threads * turns_per_thread


def test_turn_recovery_with_retry(tmp_path: Path):
    """Verify recover_incomplete_turns succeeds with retry under normal operation."""
    db_file = tmp_path / "test_recover.db"
    sm = TutorStateManager(db_path=db_file)
    lm = TurnLifecycleManager(sm)

    # Insert an incomplete turn
    turn_id, _ = generate_turn_id()
    lm.start_turn(turn_id, "student_rec", "session_rec", "chem_test")
    lm.update_stage(turn_id, TurnStage.RESPONSE_GENERATED)

    # Recover incomplete turns
    res = lm.recover_incomplete_turns()
    assert res["aborted_count"] == 1 or res["recovered_count"] == 1
