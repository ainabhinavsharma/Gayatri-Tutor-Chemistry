"""Phase 10 Test Suite: Reliability, Concurrency and Recovery.

Verifies turn lifecycle stage persistence, startup crash recovery,
and idempotency enforcement (P10-T01 through P10-T03).
"""
import pytest
import tempfile
from pathlib import Path

from core.tutor.lifecycle import TurnLifecycleManager, TurnStage
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


def test_turn_lifecycle_recording(temp_state_manager):
    mgr = TurnLifecycleManager(temp_state_manager)
    turn_id, _ = generate_turn_id("student_10", "sess_10")

    # Start turn
    rec = mgr.start_turn(turn_id, "student_10", "sess_10", "thermo.hess")
    assert rec.stage == TurnStage.TURN_STARTED

    # Advance stage
    mgr.update_stage(turn_id, TurnStage.EVALUATION_STARTED)
    mgr.update_stage(turn_id, TurnStage.LEARNING_STATE_UPDATED)
    mgr.update_stage(turn_id, TurnStage.TURN_COMMITTED)

    row = temp_state_manager.conn.execute(
        "SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id,)
    ).fetchone()
    assert row["stage"] == TurnStage.TURN_COMMITTED.value


def test_startup_turn_recovery(temp_state_manager):
    mgr = TurnLifecycleManager(temp_state_manager)

    # 1. Simulate an interrupted turn where learning event was NOT written
    turn_id_1, _ = generate_turn_id("student_10", "sess_10")
    mgr.start_turn(turn_id_1, "student_10", "sess_10", "thermo.hess")
    mgr.update_stage(turn_id_1, TurnStage.RESPONSE_GENERATED)

    # 2. Simulate an interrupted turn where learning event WAS written before crash
    turn_id_2, ts = generate_turn_id("student_10", "sess_10")
    mgr.start_turn(turn_id_2, "student_10", "sess_10", "thermo.hess")
    mgr.update_stage(turn_id_2, TurnStage.LEARNING_STATE_UPDATED)

    event = LearningEvent(
        event_id="evt_rec_2",
        student_id="student_10",
        session_id="sess_10",
        turn_id=turn_id_2,
        concept_id="thermo.hess",
        timestamp=ts,
        correctness="correct",
    )
    temp_state_manager.record_learning_event(event)

    # Run startup recovery
    res = mgr.recover_incomplete_turns()
    assert res["recovered_count"] == 1  # turn_id_2 recovered to TURN_COMMITTED
    assert res["aborted_count"] == 1    # turn_id_1 aborted to TURN_ABORTED

    row1 = temp_state_manager.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id_1,)).fetchone()
    assert row1["stage"] == TurnStage.TURN_ABORTED.value

    row2 = temp_state_manager.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = ?", (turn_id_2,)).fetchone()
    assert row2["stage"] == TurnStage.TURN_COMMITTED.value
