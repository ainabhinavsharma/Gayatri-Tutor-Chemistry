"""Multi-Turn Conversation & Session Lifecycle Regression Suite.

Verifies:
1. Brand-new session context saves satisfy Foreign Key constraints without locking.
2. Consecutive multi-turn flows (Turn 1 -> Turn 2) stream and persist completely.
3. Clarification questions asked by students during a waiting turn do not penalize mastery.
4. Conversation history and messages are fully preserved across turns.
"""
import pytest
import tempfile
from pathlib import Path

from core.session import SessionStore
from core.tutor_engine import TutorContext
from core.orchestrator import Orchestrator, TurnOptions


def test_save_tutor_context_creates_parent_session(tmp_path):
    """Verify that save_tutor_context does not raise FK constraint errors on brand new sessions."""
    db_file = tmp_path / "test_sessions.db"
    store = SessionStore(db_path=db_file)

    session_id = "brand_new_session_123"
    ctx = TutorContext(
        current_concept_id="thermo_01",
        current_concept_name="System and Surroundings",
        concept_description="Thermodynamic systems",
        subject="Thermodynamics",
        mastery=0.45,
        waiting_for_answer=True,
    )

    # Must succeed cleanly without sqlite3.IntegrityError
    store.save_tutor_context(session_id, ctx)

    # Verify session entry was created in sessions table
    with store.conn:
        row = store.conn.execute("SELECT id, message_count FROM sessions WHERE id = ?", (session_id,)).fetchone()
        assert row is not None
        assert row["id"] == session_id

    # Verify loaded context matches
    loaded = store.load_tutor_context(session_id)
    assert loaded is not None
    assert loaded.current_concept_id == "thermo_01"
    assert loaded.current_concept_name == "System and Surroundings"
    assert loaded.waiting_for_answer is True
    store.close()


def test_multi_turn_orchestrator_consecutive_stream():
    """Verify Turn 1 followed immediately by Turn 2 in the same session without database locks."""
    orch = Orchestrator()
    opts = TurnOptions(mode="chemistry_tutor")
    session_id = "multi_turn_test_session_xyz"

    # Turn 1
    t1_tokens = []
    for token, is_done in orch.stream("Can you teach me about System and Surroundings?", session_id=session_id, options=opts):
        if token:
            t1_tokens.append(token)

    assert len(t1_tokens) > 0, "Turn 1 must produce tokens"

    # Verify conversation history has Turn 1
    conv = orch.get_conversation(session_id)
    msgs = conv.get_all()
    assert len(msgs) >= 2, f"Expected user + assistant messages from Turn 1, got {len(msgs)}"
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"

    # Turn 2
    t2_tokens = []
    for token, is_done in orch.stream("What is an open system?", session_id=session_id, options=opts):
        if token:
            t2_tokens.append(token)

    assert len(t2_tokens) > 0, "Turn 2 must produce tokens without blocking or deadlocking"

    # Verify conversation history now has both turns (at least 4 messages)
    msgs = conv.get_all()
    assert len(msgs) >= 4, f"Expected at least 4 messages across 2 turns, got {len(msgs)}"
    assert msgs[2]["role"] == "user"
    assert msgs[3]["role"] == "assistant"


def test_student_question_in_tutor_turn_skips_grading():
    """Verify that a clarification question asked when tutor is waiting does not penalize mastery."""
    orch = Orchestrator()
    opts = TurnOptions(mode="chemistry_tutor")
    session_id = "student_question_session_abc"

    tutor = orch.get_tutor_engine()
    ctx = tutor.get_or_create_context(session_id)
    ctx.waiting_for_answer = True
    initial_attempts = ctx.attempts

    # Student asks a question instead of answering
    for _, _ in orch.stream("Can you explain what electronegativity is?", session_id=session_id, options=opts):
        pass

    updated_ctx = tutor.get_or_create_context(session_id)
    # Question should not have been recorded as an attempt or evaluated incorrect
    assert updated_ctx.last_attempt_correct is not False
    assert updated_ctx.attempts == initial_attempts


def test_bridge_multi_turn_consecutive(qtbot):
    """Verify that Bridge can execute Turn 1 and Turn 2 consecutively in the same session without locking."""
    from app.bridge.facade import Bridge
    bridge = Bridge()

    # Turn 1
    with qtbot.waitSignal(bridge.done, timeout=5000):
        bridge.send_message("What is a closed system?", mode="chemistry_tutor")

    assert bridge._generation_active is False

    # Turn 2 immediately in the same session
    with qtbot.waitSignal(bridge.done, timeout=5000):
        bridge.send_message("Can matter transfer across a closed boundary?", mode="chemistry_tutor")

    assert bridge._generation_active is False
