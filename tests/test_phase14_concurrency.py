"""Phase 14: Streaming and Concurrency Verification Tests (Section 20).

Verifies:
1. Turn lifecycle progression: TURN_STARTED -> EVALUATION_STARTED -> RESPONSE_GENERATED -> EVALUATION_COMPLETED -> LEARNING_STATE_UPDATED -> TURN_COMMITTED.
2. Turn failure and abort: transitions to TURN_ABORTED with error detail captured.
3. Streaming lifecycle progression and abort handling.
4. Idempotency: duplicate learning events do not double-mutate student mastery.
5. Concurrent student isolation and lock contention safety.
6. Incomplete turn crash recovery on system restart.
"""
import concurrent.futures
import pytest
from unittest.mock import patch

from core.orchestrator import Orchestrator, TurnOptions
from core.tutor.state import LearningEvent, TutorStateManager
from core.tutor.lifecycle import TurnLifecycleManager, TurnStage


def test_turn_lifecycle_submit_success(tmp_path):
    """Verify Section 20: successful submit traverses full lifecycle to TURN_COMMITTED."""
    db_path = tmp_path / "test_lifecycle_submit.db"
    state_mgr = TutorStateManager(db_path=db_path)
    orchestrator = Orchestrator(state_manager=state_mgr)

    opts = TurnOptions(mode="chemistry_tutor", student_id="student_submit_1")
    result = orchestrator.submit("What is the first law of thermodynamics?", session_id="sess_sub_1", options=opts)

    assert result.status == "SUCCESS"
    assert result.text != ""

    # Verify lifecycle entry in DB
    row = state_mgr.conn.execute(
        "SELECT turn_id, student_id, session_id, stage, error_detail FROM turn_lifecycle WHERE student_id = ?",
        ("student_submit_1",)
    ).fetchone()

    assert row is not None
    assert row["student_id"] == "student_submit_1"
    assert row["session_id"] == "sess_sub_1"
    assert row["stage"] == TurnStage.TURN_COMMITTED.value
    assert row["error_detail"] == ""


def test_turn_lifecycle_stream_success(tmp_path):
    """Verify Section 20: streaming traverses full lifecycle to TURN_COMMITTED."""
    db_path = tmp_path / "test_lifecycle_stream.db"
    state_mgr = TutorStateManager(db_path=db_path)
    orchestrator = Orchestrator(state_manager=state_mgr)

    opts = TurnOptions(mode="chemistry_tutor", student_id="student_stream_1")
    stream_gen = orchestrator.stream("Explain Hess's Law", session_id="sess_str_1", options=opts)

    tokens = []
    for token, done in stream_gen:
        if token:
            tokens.append(token)
        if done:
            break

    assert len(tokens) > 0

    row = state_mgr.conn.execute(
        "SELECT turn_id, student_id, session_id, stage, error_detail FROM turn_lifecycle WHERE student_id = ?",
        ("student_stream_1",)
    ).fetchone()

    assert row is not None
    assert row["student_id"] == "student_stream_1"
    assert row["session_id"] == "sess_str_1"
    assert row["stage"] == TurnStage.TURN_COMMITTED.value
    assert row["error_detail"] == ""


def test_turn_lifecycle_aborted_on_submit_error(tmp_path):
    """Verify Section 20: runtime error during submit marks turn as TURN_ABORTED with error detail."""
    db_path = tmp_path / "test_lifecycle_aborted.db"
    state_mgr = TutorStateManager(db_path=db_path)
    orchestrator = Orchestrator(state_manager=state_mgr)

    opts = TurnOptions(mode="chemistry_tutor", student_id="student_err_1")

    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=RuntimeError("Simulated LLM network error")):
        result = orchestrator.submit("Will this fail?", session_id="sess_err_1", options=opts)

    assert result.status == "ERROR"
    assert "error" in result.text.lower()

    row = state_mgr.conn.execute(
        "SELECT turn_id, student_id, session_id, stage, error_detail FROM turn_lifecycle WHERE student_id = ?",
        ("student_err_1",)
    ).fetchone()

    assert row is not None
    assert row["stage"] == TurnStage.TURN_ABORTED.value
    assert "Simulated LLM network error" in row["error_detail"]


def test_turn_lifecycle_aborted_on_stream_error(tmp_path):
    """Verify Section 20: runtime error during stream marks turn as TURN_ABORTED with error detail."""
    db_path = tmp_path / "test_stream_aborted.db"
    state_mgr = TutorStateManager(db_path=db_path)
    orchestrator = Orchestrator(state_manager=state_mgr)

    opts = TurnOptions(mode="chemistry_tutor", student_id="student_stream_err_1")

    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=RuntimeError("Simulated stream crash")):
        stream_gen = orchestrator.stream("Will stream fail?", session_id="sess_str_err", options=opts)
        results = list(stream_gen)

    assert any("Simulated stream crash" in text for text, is_final in results)

    row = state_mgr.conn.execute(
        "SELECT turn_id, student_id, session_id, stage, error_detail FROM turn_lifecycle WHERE student_id = ?",
        ("student_stream_err_1",)
    ).fetchone()

    assert row is not None
    assert row["stage"] == TurnStage.TURN_ABORTED.value
    assert "Simulated stream crash" in row["error_detail"]


def test_learning_event_idempotency(tmp_path):
    """Verify Section 20: async operations are idempotent; duplicate event does not double-mutate mastery."""
    db_path = tmp_path / "test_idempotency.db"
    state_mgr = TutorStateManager(db_path=db_path)

    event = LearningEvent(
        event_id="evt_idem_101",
        student_id="student_idem",
        session_id="sess_idem",
        turn_id="turn_idem_1",
        concept_id="chem.thermo.enthalpy",
        difficulty=0.6,
        question_type="conceptual",
        correctness="correct",
        confidence=0.95,
        source="practice",
    )

    # First insertion succeeds and increments mastery
    first_res = state_mgr.record_learning_event(event)
    assert first_res is True

    mastery_first = state_mgr.get_student_concept_mastery("student_idem", "chem.thermo.enthalpy")
    assert mastery_first.exposure_count == 1
    assert mastery_first.correct_count == 1
    initial_mastery = mastery_first.mastery
    assert initial_mastery > 0.0

    # Second insertion with exact same event_id is rejected idempotently
    second_res = state_mgr.record_learning_event(event)
    assert second_res is False

    mastery_second = state_mgr.get_student_concept_mastery("student_idem", "chem.thermo.enthalpy")
    assert mastery_second.exposure_count == 1
    assert mastery_second.correct_count == 1
    assert mastery_second.mastery == initial_mastery

    # Exactly 1 row in learning_events table
    count = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM learning_events WHERE event_id = ?", ("evt_idem_101",)
    ).fetchone()["cnt"]
    assert count == 1


def test_concurrent_turns_student_isolation(tmp_path):
    """Verify Section 20: concurrent student turns run safely with student isolation and no lock issues."""
    db_path = tmp_path / "test_concurrent.db"
    state_mgr = TutorStateManager(db_path=db_path)

    def run_student_turn(student_idx: int):
        student_id = f"student_conc_{student_idx}"
        session_id = f"sess_conc_{student_idx}"
        orch = Orchestrator(state_manager=state_mgr)
        opts = TurnOptions(mode="chemistry_tutor", student_id=student_id)
        res = orch.submit(f"Explain thermodynamics concept {student_idx}", session_id=session_id, options=opts)
        return student_id, res.status

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_student_turn, i) for i in range(4)]
        results = [f.result() for f in futures]

    for student_id, status in results:
        assert status == "SUCCESS"
        row = state_mgr.conn.execute(
            "SELECT stage FROM turn_lifecycle WHERE student_id = ?", (student_id,)
        ).fetchone()
        assert row is not None
        assert row["stage"] == TurnStage.TURN_COMMITTED.value

    # Verify 4 distinct records exist
    total_turns = state_mgr.conn.execute(
        "SELECT COUNT(DISTINCT student_id) as cnt FROM turn_lifecycle WHERE student_id LIKE 'student_conc_%'"
    ).fetchone()["cnt"]
    assert total_turns == 4


def test_startup_turn_recovery(tmp_path):
    """Verify Section 20: incomplete turns are cleanly recovered or aborted on restart."""
    db_path = tmp_path / "test_recovery.db"
    state_mgr = TutorStateManager(db_path=db_path)
    lifecycle = TurnLifecycleManager(state_mgr)

    # 1. Incomplete turn without learning event -> should ABORT
    state_mgr.conn.execute("""
        INSERT INTO turn_lifecycle (turn_id, student_id, session_id, concept_id, stage, started_at, updated_at)
        VALUES ('turn_rec_1', 's_rec_1', 'sess_rec_1', 'c1', 'RESPONSE_GENERATED', '2026-09-20T10:00:00', '2026-09-20T10:00:00')
    """)

    # 2. Incomplete turn WITH learning event -> should COMMIT
    state_mgr.conn.execute("""
        INSERT INTO turn_lifecycle (turn_id, student_id, session_id, concept_id, stage, started_at, updated_at)
        VALUES ('turn_rec_2', 's_rec_2', 'sess_rec_2', 'c2', 'EVALUATION_COMPLETED', '2026-09-20T10:00:00', '2026-09-20T10:00:00')
    """)
    state_mgr.conn.execute("""
        INSERT INTO learning_events (event_id, student_id, session_id, turn_id, concept_id, timestamp, correctness)
        VALUES ('evt_rec_2', 's_rec_2', 'sess_rec_2', 'turn_rec_2', 'c2', '2026-09-20T10:00:05', 'correct')
    """)

    # Run startup recovery
    rec_result = lifecycle.recover_incomplete_turns()
    assert rec_result["aborted_count"] == 1
    assert rec_result["recovered_count"] == 1

    # Verify stage transitions
    row1 = state_mgr.conn.execute("SELECT stage, error_detail FROM turn_lifecycle WHERE turn_id = 'turn_rec_1'").fetchone()
    assert row1["stage"] == TurnStage.TURN_ABORTED.value
    assert "interrupted" in row1["error_detail"].lower()

    row2 = state_mgr.conn.execute("SELECT stage FROM turn_lifecycle WHERE turn_id = 'turn_rec_2'").fetchone()
    assert row2["stage"] == TurnStage.TURN_COMMITTED.value
