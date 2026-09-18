"""Tests for session persistence."""

from pathlib import Path
from core.session import SessionStore

class DummyConversation:
    def __init__(self, messages):
        self.messages = messages
    def get_all(self):
        return self.messages

def test_session_save_and_load(tmp_path: Path):
    db_path = tmp_path / "sessions.db"
    store = SessionStore(db_path)
    
    messages = [
        {"role": "user", "content": "hello", "agent_name": "", "timestamp": "2026-01-01T00:00:00"},
        {"role": "assistant", "content": "hi", "agent_name": "Tutor", "timestamp": "2026-01-01T00:00:01"}
    ]
    conv = DummyConversation(messages)
    
    store.save_session("sess_1", conv)
    
    loaded = store.load_session("sess_1")
    assert len(loaded) == 2
    assert loaded[0]["content"] == "hello"
    assert loaded[1]["agent_name"] == "Tutor"
    
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["id"] == "sess_1"
    
    store.close()
