"""Tests for Phase 22: Frontend/API Reliability (Section 28).

Verifies all 10 frontend/API interaction states:
1. loading
2. timeout
3. retry
4. duplicate submit
5. stream disconnect
6. partial stream
7. refresh (session reload)
8. logout/login (new_chat/session isolation)
9. multiple tabs (concurrent sessions)
10. mode switch

Invariant: A failed API request must never update learning progress as successful.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.bridge.facade import Bridge
from core.orchestrator import Orchestrator, TurnOptions
from core.mode import AppMode
from core.tutor.state import TutorStateManager
from core.tutor.lifecycle import TurnStage
from core.learning.progress import ProgressService
from core.security.rate_limiter import get_governor, RateLimitExceededError


@pytest.fixture
def state_mgr(tmp_path):
    """Provide a fresh TutorStateManager with an isolated SQLite DB."""
    return TutorStateManager(db_path=tmp_path / "test_frontend_api.db")


@pytest.fixture
def orchestrator(state_mgr):
    """Provide an Orchestrator connected to the test state manager."""
    return Orchestrator(state_manager=state_mgr)


def test_loading_state_lifecycle(orchestrator, qtbot):
    """Verify loading state (_generation_active) transitions correctly during generation and completion."""
    bridge = Bridge()
    bridge._orchestrator = orchestrator

    assert bridge._generation_active is False

    with qtbot.waitSignal(bridge.done, timeout=5000):
        bridge.send_message("What is enthalpy?", mode="general_assistant")

    assert bridge._generation_active is False


def test_duplicate_submit_blocked():
    """Verify duplicate submissions while generation is active are blocked."""
    bridge = Bridge()
    bridge._generation_active = True

    error_messages = []
    bridge.error.connect(lambda msg: error_messages.append(msg))

    bridge.send_message("Second message while first is generating")

    assert len(error_messages) == 1
    assert "Please wait for the current response to finish" in error_messages[0]


def test_timeout_handling_aborts_cleanly(orchestrator, state_mgr):
    """Verify timeout during turn execution triggers TURN_ABORTED and does not update mastery."""
    opts = TurnOptions(mode="chemistry_tutor", student_id="std_timeout_1")

    # Force timeout by patching runtime stream to raise TimeoutError
    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=TimeoutError("Request timed out")):
        res = orchestrator.submit("Explain thermodynamics", session_id="sess_timeout", options=opts)

    assert res.status == "ERROR"
    assert "error" in res.routing_reason

    # Verify turn lifecycle is TURN_ABORTED
    row = state_mgr.conn.execute(
        "SELECT stage, error_detail FROM turn_lifecycle WHERE student_id = ?", ("std_timeout_1",)
    ).fetchone()
    assert row is not None
    assert row["stage"] == TurnStage.TURN_ABORTED.value
    assert "Request timed out" in (row["error_detail"] or "")

    # Invariant: Progress must NOT show success
    mastery_rec = state_mgr.get_student_concept_mastery("std_timeout_1", "thermo.first_law")
    assert mastery_rec.exposure_count == 0
    assert mastery_rec.mastery == 0.0


def test_retry_after_failure(orchestrator, state_mgr):
    """Verify a turn that fails can be retried, and only the successful retry updates learning state."""
    student_id = "std_retry_1"
    session_id = "sess_retry_1"
    opts = TurnOptions(mode="chemistry_tutor", student_id=student_id)

    # 1. First attempt fails due to simulated runtime exception
    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=RuntimeError("Transient GPU failure")):
        res1 = orchestrator.submit("What is Hess's law?", session_id=session_id, options=opts)
    assert res1.status == "ERROR"

    # Mastery must be 0 after failed attempt
    m1 = state_mgr.get_student_concept_mastery(student_id, "thermo.hess_law")
    assert m1.exposure_count == 0

    # 2. Retry succeeds
    res2 = orchestrator.submit("What is Hess's law?", session_id=session_id, options=opts)
    assert res2.status == "SUCCESS"

    # Turn lifecycle must show TURN_COMMITTED for the retry
    committed_turns = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM turn_lifecycle WHERE student_id = ? AND stage = ?",
        (student_id, TurnStage.TURN_COMMITTED.value),
    ).fetchone()["cnt"]
    assert committed_turns == 1


def test_stream_disconnect_and_partial_stream(orchestrator, state_mgr):
    """Verify stream disconnection / abort mid-stream triggers TURN_ABORTED and rollback."""
    student_id = "std_disconnect_1"
    session_id = "sess_disconnect_1"
    opts = TurnOptions(mode="chemistry_tutor", student_id=student_id)

    def failing_stream(*args, **kwargs):
        yield "Partial token 1 "
        yield "Partial token 2 "
        raise ConnectionResetError("Client disconnected")

    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=failing_stream):
        tokens = list(orchestrator.stream("Explain Gibbs energy", session_id=session_id, options=opts))

    # Must yield error and terminate
    assert any("Client disconnected" in t[0] for t in tokens)

    # Turn lifecycle must record TURN_ABORTED
    row = state_mgr.conn.execute(
        "SELECT stage, error_detail FROM turn_lifecycle WHERE student_id = ?", (student_id,)
    ).fetchone()
    assert row is not None
    assert row["stage"] == TurnStage.TURN_ABORTED.value
    assert "Client disconnected" in row["error_detail"]


def test_refresh_session_reload(orchestrator, state_mgr):
    """Verify session reload (refresh) restores conversation and tutor context accurately."""
    bridge = Bridge()
    bridge._orchestrator = orchestrator

    # Populate session with messages
    session_id = "sess_refresh_test"
    conv = orchestrator.new_session(session_id)
    conv.add("user", "Hello tutor", agent_name="chemistry_tutor")
    conv.add("assistant", "Hello! What chemistry topic would you like to explore?", agent_name="chemistry_tutor")

    # Persist session to store
    from core.session import get_session_store
    store = get_session_store()
    store.save_session(session_id, conv)

    # Load session into bridge
    bridge.load_session_id(session_id)
    assert bridge._session_id == session_id

    loaded_conv = orchestrator.get_conversation(session_id)
    assert len(loaded_conv.get_all()) == 2
    assert loaded_conv.get_all()[0]["content"] == "Hello tutor"


def test_logout_login_and_new_chat():
    """Verify new_chat() creates an isolated session and resets generation state."""
    bridge = Bridge()
    old_session_id = bridge._session_id

    bridge.new_chat()

    assert bridge._session_id != old_session_id
    assert bridge._generation_active is False


def test_multiple_tabs_concurrent_sessions(orchestrator):
    """Verify two concurrent sessions maintain completely separate conversation states."""
    conv1 = orchestrator.new_session("tab_session_1")
    conv2 = orchestrator.new_session("tab_session_2")

    conv1.add("user", "Question from Tab 1")
    conv2.add("user", "Question from Tab 2")

    assert len(conv1.get_all()) == 1
    assert conv1.get_all()[0]["content"] == "Question from Tab 1"

    assert len(conv2.get_all()) == 1
    assert conv2.get_all()[0]["content"] == "Question from Tab 2"


def test_mode_switch_isolation(orchestrator, state_mgr):
    """Verify switching between General Assistant and Chemistry Tutor preserves strict state isolation.

    Core Invariant: General Assistant activity != Chemistry learning state
    """
    student_id = "std_mode_switch"

    # 1. General Assistant turn
    opts_gen = TurnOptions(mode="general_assistant", student_id=student_id)
    res_gen = orchestrator.submit("Write a poem about molecules", session_id="sess_mode_gen", options=opts_gen)
    assert res_gen.status == "SUCCESS"

    # General Assistant turn must NOT touch turn_lifecycle or mastery
    turns_count = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM turn_lifecycle WHERE student_id = ?", (student_id,)
    ).fetchone()["cnt"]
    assert turns_count == 0

    events_count = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM learning_events WHERE student_id = ?", (student_id,)
    ).fetchone()["cnt"]
    assert events_count == 0

    # 2. Switch to Chemistry Tutor turn
    opts_chem = TurnOptions(mode="chemistry_tutor", student_id=student_id)
    res_chem = orchestrator.submit("Explain enthalpy", session_id="sess_mode_chem", options=opts_chem)
    assert res_chem.status == "SUCCESS"

    # Chemistry Tutor turn MUST be tracked in turn_lifecycle
    chem_turns = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM turn_lifecycle WHERE student_id = ?", (student_id,)
    ).fetchone()["cnt"]
    assert chem_turns == 1


def test_failed_api_request_never_updates_progress(orchestrator, state_mgr):
    """Core Invariant Test: A failed API request must never update learning progress as successful."""
    student_id = "std_invariant_fail"
    progress_svc = ProgressService(state_mgr)

    # Baseline progress: 0 exposure, 0 mastery
    initial_prog = progress_svc.get_concept_progress(student_id, "thermo.first_law")
    assert initial_prog["exposure_count"] == 0
    assert initial_prog["mastery"] == 0.0
    assert initial_prog["status"] == "NEW"

    # 1. Validation failure (path traversal in session_id)
    res1 = orchestrator.submit("What is enthalpy?", session_id="../bad_sess")
    assert res1.status == "ERROR"

    prog_after_val = progress_svc.get_concept_progress(student_id, "thermo.first_law")
    assert prog_after_val["exposure_count"] == 0
    assert prog_after_val["mastery"] == 0.0

    # 2. Rate limit failure
    governor = get_governor()
    governor.turn_limiter.reset()
    governor.turn_limiter.max_requests = 0  # Block all

    try:
        opts = TurnOptions(mode="chemistry_tutor", student_id=student_id)
        res2 = orchestrator.submit("What is enthalpy?", session_id="sess_ok", options=opts)
        assert res2.status == "ERROR"
        assert res2.routing_reason == "rate_limit_exceeded"

        prog_after_rate = progress_svc.get_concept_progress(student_id, "thermo.first_law")
        assert prog_after_rate["exposure_count"] == 0
        assert prog_after_rate["mastery"] == 0.0
    finally:
        governor.turn_limiter.max_requests = 30
        governor.turn_limiter.reset()

    # 3. Model failure
    with patch("core.runtimes.chemistry.ChemistryTutorRuntime.stream", side_effect=RuntimeError("Model crashed")):
        opts = TurnOptions(mode="chemistry_tutor", student_id=student_id)
        res3 = orchestrator.submit("What is enthalpy?", session_id="sess_ok", options=opts)
        assert res3.status == "ERROR"

    final_prog = progress_svc.get_concept_progress(student_id, "thermo.first_law")
    assert final_prog["exposure_count"] == 0
    assert final_prog["mastery"] == 0.0
    assert final_prog["status"] == "NEW"
