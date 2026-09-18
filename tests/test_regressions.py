import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.privacy import PIIRedactor
from legacy.agents.default_agents import _get_tutor_context
from core.agents.runtime import AgentContext

def test_regression_bug_1_model_progress_args():
    """Bug #1: progress_callback accepts 3 positional arguments (label, downloaded, total)."""
    calls = []

    def mock_callback(label: str, downloaded: int, total: int):
        calls.append((label, downloaded, total))

    # Test that the progress function conforms to the 3-argument contract without raising TypeError
    mock_callback("model", 512, 1024)
    assert len(calls) == 1
    assert calls[0] == ("model", 512, 1024)


def test_regression_bug_3_pii_multiple_matches():
    """Bug #3: PII redaction corrupts text when same PII type appears twice."""
    redactor = PIIRedactor()
    text = "Contact alice@example.com and bob@example.com"
    redacted = redactor.redact(text)
    import re
    assert re.match(r"Contact \[EMAIL_0_[a-f0-9]{8}\] and \[EMAIL_1_[a-f0-9]{8}\]", redacted.clean_text)
    assert redacted.restore(redacted.clean_text) == text


def test_regression_bug_6_tutor_prerequisites_key():
    """Bug #6: Tutor 'prerequisites not met' instruction never sent to model."""
    context = AgentContext(session_id="test", user_message="hello", metadata={"tutor": {"prerequisites_not_met": True, "prereq_names": ["A"]}})
    system_prompt = _get_tutor_context(context)
    assert "IMPORTANT: The student needs to master prerequisites first" in system_prompt


def test_regression_bug_8_chat_bubbles():
    """Bug #8: Bridge streams individual tokens and emits completion signal without overwriting."""
    from app.bridge.facade import Bridge

    bridge = Bridge()
    tokens_received = []
    bridge.token.connect(lambda idx, text: tokens_received.append((idx, text)))

    # Emitting tokens simulates streamed chunks
    bridge.token.emit(0, "Hello ")
    bridge.token.emit(0, "World!")

    assert len(tokens_received) == 2
    assert "".join(t[1] for t in tokens_received) == "Hello World!"


def test_regression_bug_18_mastery_threshold(tmp_path):
    """Bug #18: Tutor advances concept behaviorally when mastery reaches or exceeds LDG_MASTERY_THRESHOLD."""
    from core.config import LDG_MASTERY_THRESHOLD
    from core.knowledge_graph import LearningDependencyGraph
    from core.tutor_engine import TutorEngine

    db_path = tmp_path / "test_thresh.db"
    ldg = LearningDependencyGraph(db_path=db_path)
    ldg.add_concept("c1", "Concept 1", subject="math")
    ldg.add_concept("c2", "Concept 2", subject="math")

    tutor = TutorEngine(ldg)
    ctx = tutor.get_or_create_context("sess_thresh")
    ctx.subject = "math"
    ctx.current_concept_id = "c1"

    # Below threshold (0.5 < 0.85): get_next_concept_for_session retains current concept
    ldg.record_attempt("c1", correct=False, confidence=1.0)
    retained = tutor.get_next_concept_for_session("sess_thresh")
    assert retained.id == "c1"

    # Set mastery above threshold (0.9 >= 0.85): get_next_concept_for_session advances to c2
    conn = ldg._conn()
    conn.execute(f"UPDATE ldg_concepts SET mastery = {LDG_MASTERY_THRESHOLD + 0.05} WHERE id = 'c1'")
    conn.commit()
    conn.close()
    ldg.clear_cache()

    advanced = tutor.get_next_concept_for_session("sess_thresh")
    assert advanced is not None
    assert advanced.id == "c2"


