from core.session import SessionStore
from core.tutor_engine import TutorContext, TutorEngine
from core.knowledge_graph import LearningDependencyGraph
from core.orchestrator import Orchestrator


def test_session_store_tutor_context_persistence(tmp_path):
    """Audit #10: Verify TutorContext is persisted and loaded from SQLite."""
    db_path = tmp_path / "test_tutor.db"
    store = SessionStore(db_path)

    ctx = TutorContext(
        current_concept_id="python_loops",
        current_concept_name="Loops in Python",
        concept_description="For and while loops",
        subject="computer_science",
        mastery=0.72,
        waiting_for_answer=True,
        last_response_type="question",
        last_attempt_correct=False,
    )

    class DummyConv:
        def get_all(self):
            return [{"role": "user", "content": "Tell me about loops", "timestamp": "2026-01-01T00:00:00"}]

    # Save session with tutor context
    store.save_session("sess_tutor_1", DummyConv(), tutor_context=ctx)

    # Load tutor context back
    loaded_ctx = store.load_tutor_context("sess_tutor_1")
    assert loaded_ctx is not None
    assert loaded_ctx.current_concept_id == "python_loops"
    assert loaded_ctx.current_concept_name == "Loops in Python"
    assert loaded_ctx.subject == "computer_science"
    assert abs(loaded_ctx.mastery - 0.72) < 1e-4
    assert loaded_ctx.waiting_for_answer is True
    assert loaded_ctx.last_response_type == "question"
    assert loaded_ctx.last_attempt_correct is False

    # Verify deletion cleans up tutor context
    store.delete_session("sess_tutor_1")
    assert store.load_tutor_context("sess_tutor_1") is None
    store.close()


def test_tutor_continuation_after_restart(tmp_path, monkeypatch):
    """Audit #32: End-to-end test for chat -> save -> restart -> load -> tutor continuation."""
    db_path = tmp_path / "test_app_restart.db"
    store = SessionStore(db_path)
    monkeypatch.setattr("core.session.get_session_store", lambda: store)

    ldg = LearningDependencyGraph()
    tutor1 = TutorEngine(ldg)

    # Student starts a session and tutor is waiting for answer on variables
    session_id = "sess_learn_variables"
    ctx1 = tutor1.get_or_create_context(session_id)
    ctx1.current_concept_id = "vars_1"
    ctx1.current_concept_name = "Variables"
    ctx1.mastery = 0.55
    tutor1.set_waiting_for_answer(session_id)

    class DummyConv:
        def get_all(self):
            return [
                {"role": "user", "content": "What is a variable?", "timestamp": "2026-01-01T00:00:00"},
                {"role": "assistant", "content": "Can you give an example?", "timestamp": "2026-01-01T00:00:01"},
            ]

    # Save session
    store.save_session(session_id, DummyConv(), tutor_context=ctx1)

    # Simulate restart: fresh TutorEngine and Orchestrator with empty memory
    tutor2 = TutorEngine(ldg)
    orch = Orchestrator()
    monkeypatch.setattr("core.orchestrator._get_tutor_engine", lambda: tutor2)

    # Load session
    messages = store.load_session(session_id)
    tutor_ctx = store.load_tutor_context(session_id)
    orch.load_session(session_id, messages, tutor_context=tutor_ctx)

    # Check that tutor2 now has the exact context restored
    ctx2 = tutor2.get_or_create_context(session_id)
    assert ctx2.current_concept_id == "vars_1"
    assert ctx2.current_concept_name == "Variables"
    assert abs(ctx2.mastery - 0.55) < 1e-4
    assert ctx2.waiting_for_answer is True

    store.close()
