from core.tutor_engine import TutorEngine
from core.knowledge_graph import LearningDependencyGraph
from core.orchestrator import _evaluate_tutor_response

def test_evaluate_tutor_response_mastery_update(monkeypatch, tmp_path):
    from core.session import SessionStore
    store = SessionStore(tmp_path / "test_session.db")
    monkeypatch.setattr("core.session.get_session_store", lambda: store)

    ldg = LearningDependencyGraph(db_path=tmp_path / "test_ldg.db")
    # Add a mock concept
    conn = ldg._conn()
    conn.execute("INSERT OR REPLACE INTO ldg_concepts (id, name, subject) VALUES ('test_concept', 'Test Concept', 'test_subject')")
    conn.commit()
    conn.close()
    ldg.clear_cache()

    tutor = TutorEngine(ldg)
    monkeypatch.setattr("core.orchestrator._get_tutor_engine", lambda: tutor)
    monkeypatch.setattr("core.orchestrator._get_ldg", lambda: ldg)
    
    # Mock LLM Evaluator based on input
    def mock_chat(messages, **kwargs):
        user_msg = messages[-1]["content"].lower()
        if "well, i was thinking" in user_msg:
            return '{"correct": null, "confidence": 0.5}'
        elif "i don't know" in user_msg:
            return '{"correct": false, "confidence": 0.9}'
        elif "yes, i think it is" in user_msg:
            return '{"correct": true, "confidence": 0.9}'
        elif "ok" in user_msg:
            return '{"correct": false, "confidence": 0.9}'
        elif "nope that is definitely not right" in user_msg:
            return '{"correct": false, "confidence": 0.9}'
        return '{"correct": null, "confidence": 1.0}'
        
    monkeypatch.setattr("core.providers.local.LocalProvider.chat", mock_chat)

    # Set context
    ctx = tutor.get_or_create_context("test_session")
    ctx.current_concept_id = "test_concept"
    ctx.current_concept_name = "Test Concept"
    ctx.mastery = 0.5
    ctx.waiting_for_answer = True

    # Test: Uncertain answer (long but not clearly correct/incorrect)
    _evaluate_tutor_response("test_session", "well, I was thinking about it and I am not really sure what the exact answer would be here")
    assert ctx.mastery == 0.5  # unchanged!

    old_mastery = ctx.mastery
    
    # Test: "I don't know"
    ctx.waiting_for_answer = True
    _evaluate_tutor_response("test_session", "i don't know")
    assert ctx.mastery < old_mastery  # Decreased because incorrect

    # Test: Correct answer
    old_mastery = ctx.mastery
    ctx.waiting_for_answer = True
    _evaluate_tutor_response("test_session", "yes, I think it is")
    assert ctx.mastery > old_mastery  # Increased because correct

    # Test: Short incorrect
    old_mastery = ctx.mastery
    ctx.waiting_for_answer = True
    _evaluate_tutor_response("test_session", "ok")
    assert ctx.mastery < old_mastery  # Decreased

    # Test: Long incorrect
    old_mastery = ctx.mastery
    ctx.waiting_for_answer = True
    _evaluate_tutor_response("test_session", "nope that is definitely not right and I disagree with this entire concept completely")
    assert ctx.mastery < old_mastery  # Decreased

