import pytest
from core.orchestrator import Orchestrator
from app.bridge import Bridge


def test_stream_error_does_not_persist_error_as_assistant_message(monkeypatch):
    """Audit #17: Verify conversation history is not contaminated with error text."""
    orch = Orchestrator()
    session_id = "test_err_sess_1"

    # Force LocalProvider.chat_stream to fail
    def failing_stream(*args, **kwargs):
        raise ConnectionError("Provider failed to connect")

    monkeypatch.setattr("core.providers.local.LocalProvider.chat_stream", failing_stream)

    # Calling stream should raise an error
    with pytest.raises(RuntimeError, match="Streaming failed"):
        list(orch.stream("Hello world", session_id=session_id))

    # Inspect conversation
    conv = orch.get_conversation(session_id)
    messages = conv.get_all()

    # User message should be recorded
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello world"

    # Ensure NO assistant message containing raw error text was stored
    for msg in messages:
        assert msg["role"] != "assistant"
        assert "Provider failed to connect" not in msg["content"]


def test_stream_emits_single_terminal_event_on_failure(monkeypatch, qtbot):
    """Audit #18: Verify bridge emits done exactly once and emits error on failure."""
    bridge = Bridge()
    orch = bridge._get_orchestrator()

    def failing_stream(*args, **kwargs):
        raise ConnectionError("Model crashed")

    monkeypatch.setattr("core.providers.local.LocalProvider.chat_stream", failing_stream)

    done_calls = []
    error_calls = []

    bridge.done.connect(lambda: done_calls.append(True))
    bridge.error.connect(lambda err: error_calls.append(err))

    bridge.send_message("Test failure")

    # Exactly one error and one done
    assert len(error_calls) == 1
    assert "Model crashed" in error_calls[0]
    assert len(done_calls) == 1


def test_submit_error_does_not_persist_error_as_assistant_message(monkeypatch):
    """Audit #17: Verify submit does not store raw exception text as assistant message."""
    orch = Orchestrator()
    session_id = "test_err_sess_2"

    def failing_chat(*args, **kwargs):
        raise ConnectionError("Local provider down")

    monkeypatch.setattr("core.providers.local.LocalProvider.chat", failing_chat)

    res = orch.submit("Calculate this", session_id=session_id)
    assert "error" in res.routing_reason

    # Check conversation
    conv = orch.get_conversation(session_id)
    messages = conv.get_all()

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Calculate this"

    for msg in messages:
        assert msg["role"] != "assistant"
    assert res.status == "ERROR"


def test_submit_agent_error_status_and_transaction_rollback(tmp_path, monkeypatch):
    """Verify when an agent returns status=ERROR, submit returns status=ERROR and rolls back tutor transaction."""
    from core.knowledge_graph import LearningDependencyGraph
    from core.tutor_engine import TutorEngine
    from core.agents.registry import AgentResponse
    from core.orchestrator import TurnOptions

    ldg = LearningDependencyGraph(tmp_path / "ldg.db")
    ldg.add_concept("vars", "Variables", "Concept 1", difficulty=0.3, subject="Python")
    tutor = TutorEngine(ldg)

    orch = Orchestrator(tutor_engine=tutor, ldg=ldg)
    session_id = "test_agent_err_submit"

    # Set tutor waiting for answer on 'vars'
    ctx = tutor.get_or_create_context(session_id)
    ctx.current_concept_id = "vars"
    ctx.waiting_for_answer = True
    orig_mastery = ldg.get_mastery("vars")

    # Mock runtime to return AgentResponse with status="ERROR"
    def mock_process(msg, context, spec=None):
        return AgentResponse(text="Agent crashed", agent_name="Tutor", status="ERROR")

    monkeypatch.setattr(orch.runtime, "process", mock_process)

    # Submit a turn forced to Tutor
    opts = TurnOptions(forced_agent="Tutor")
    res = orch.submit("yes, I got it right", session_id=session_id, options=opts)

    assert res.status == "ERROR"
    assert "Agent crashed" in res.text

    # Verify tutor transaction rolled back: mastery is unchanged and tutor is not in committed post-response state
    assert ldg.get_mastery("vars") == orig_mastery


def test_stream_agent_error_status_and_transaction_rollback(tmp_path, monkeypatch):
    """Verify when an agent returns status=ERROR in stream, it rolls back tutor transaction and yields error."""
    from core.knowledge_graph import LearningDependencyGraph
    from core.tutor_engine import TutorEngine
    from core.agents.registry import AgentResponse
    from core.orchestrator import TurnOptions

    ldg = LearningDependencyGraph(tmp_path / "ldg.db")
    ldg.add_concept("loops", "Loops", "Concept 2", difficulty=0.4, subject="Python")
    tutor = TutorEngine(ldg)

    orch = Orchestrator(tutor_engine=tutor, ldg=ldg)
    session_id = "test_agent_err_stream"

    ctx = tutor.get_or_create_context(session_id)
    ctx.current_concept_id = "loops"
    ctx.waiting_for_answer = True
    orig_mastery = ldg.get_mastery("loops")

    def mock_process(msg, context, spec=None):
        return AgentResponse(text="Agent stream error occurred", agent_name="Tutor", status="ERROR")

    monkeypatch.setattr(orch.runtime, "process", mock_process)

    opts = TurnOptions(forced_agent="Tutor")
    tokens = list(orch.stream("yes", session_id=session_id, options=opts))

    assert len(tokens) == 1
    tok, is_done = tokens[0]
    assert is_done is True
    assert "Agent stream error occurred" in tok

    # Mastery should be rolled back to original
    assert ldg.get_mastery("loops") == orig_mastery

