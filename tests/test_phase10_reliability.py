"""Tests for Phase 10: Concurrency & Reliability Re-Audit (P10-T01 to P10-T04)."""
import uuid
import pytest
from core.tutor.state import TutorStateManager, LearningEvent
from core.tutor.lifecycle import TurnLifecycleManager, TurnStage


def test_turn_lifecycle_recording(tmp_path):
    """Test recording turn lifecycle stage progression in SQLite."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    mgr = TurnLifecycleManager(state_manager=sm)

    turn_id = f"turn_{uuid.uuid4().hex[:8]}"

    # 1. Start Turn
    rec = mgr.start_turn(
        turn_id=turn_id,
        student_id="student_rel_1",
        session_id="sess_rel_1",
        concept_id="thermo.hess",
    )
    assert rec.stage == TurnStage.TURN_STARTED

    # 2. Advance to EVALUATION_STARTED
    mgr.update_stage(turn_id, TurnStage.EVALUATION_STARTED)
    cursor = sm.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id,))
    assert cursor.fetchone()["stage"] == TurnStage.EVALUATION_STARTED.value

    # 3. Advance to TURN_COMMITTED
    mgr.update_stage(turn_id, TurnStage.TURN_COMMITTED)
    cursor = sm.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id,))
    assert cursor.fetchone()["stage"] == TurnStage.TURN_COMMITTED.value


def test_startup_turn_recovery_committed(tmp_path):
    """Test startup recovery committing interrupted turns where learning events were already recorded."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    mgr = TurnLifecycleManager(state_manager=sm)

    turn_id = "turn_interrupted_1"

    # Seed an incomplete turn stage in database
    mgr.start_turn(
        turn_id=turn_id,
        student_id="student_rel_2",
        session_id="sess_rel_2",
        concept_id="thermo.gibbs",
    )
    mgr.update_stage(turn_id, TurnStage.RESPONSE_GENERATED)

    # Record learning event for this turn ID to simulate post-event crash
    event = LearningEvent(
        event_id=f"evt_{turn_id}",
        student_id="student_rel_2",
        session_id="sess_rel_2",
        turn_id=turn_id,
        concept_id="thermo.gibbs",
        correctness="correct",
    )
    sm.record_learning_event(event)

    # Perform startup recovery
    summary = mgr.recover_incomplete_turns()
    assert summary["recovered_count"] == 1
    assert summary["aborted_count"] == 0

    # Verify stage in DB is now TURN_COMMITTED
    cursor = sm.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id,))
    assert cursor.fetchone()["stage"] == TurnStage.TURN_COMMITTED.value


def test_startup_turn_recovery_aborted(tmp_path):
    """Test startup recovery marking uncommitted interrupted turns as TURN_ABORTED."""
    db_path = str(tmp_path / "test_tutor.db")
    sm = TutorStateManager(db_path=db_path)
    mgr = TurnLifecycleManager(state_manager=sm)

    turn_id = "turn_interrupted_pre_event"

    # Seed incomplete turn without learning event
    mgr.start_turn(
        turn_id=turn_id,
        student_id="student_rel_3",
        session_id="sess_rel_3",
        concept_id="inorganic.periodic",
    )
    mgr.update_stage(turn_id, TurnStage.EVALUATION_STARTED)

    # Perform startup recovery
    summary = mgr.recover_incomplete_turns()
    assert summary["recovered_count"] == 0
    assert summary["aborted_count"] == 1

    # Verify stage in DB is now TURN_ABORTED
    cursor = sm.conn.execute("SELECT stage, error_detail FROM turn_lifecycle WHERE turn_id = ?", (turn_id,))
    row = cursor.fetchone()
    assert row["stage"] == TurnStage.TURN_ABORTED.value
    assert "interrupted" in row["error_detail"].lower()
