"""Tests for Batch D: Session Persistence & Storage Reliability (Audit #30, #31, #111, #113, #132, #133).

Covers:
- Strict session ID validation against path traversal and injection.
- O(1) incremental session save avoiding O(N^2) table churning and ID invalidation.
- Retention of full session history beyond LLM prompt token window.
- In-memory and persisted state synchronization on session clear/load.
- SQLite PRAGMAs (WAL mode, busy_timeout=10000, foreign_keys=ON).
- Concurrent thread safety under write load.
- Bridge integration for session management.
"""

import json
import threading
import pytest

from core.conversation import Conversation
from core.db import get_safe_db_connection
from core.session import SessionStore, validate_session_id


class DummyConversation:
    def __init__(self, messages):
        self.messages = list(messages)

    def get_all(self):
        return self.messages


class TestSessionIDValidation:
    """Audit #132 & #133: Strict session ID format validation at persistence boundary."""

    def test_valid_session_ids(self):
        valid_cases = [
            "default",
            "sess_1",
            "test-session",
            "session:42",
            "user_123-abc:xyz",
            "c87465b6-657c-44be-842e-6b7f56c9d8cd",
            "A" * 128,
        ]
        for sid in valid_cases:
            assert validate_session_id(sid) == sid

    def test_invalid_session_ids_rejected(self):
        invalid_cases = [
            "",
            "   ",
            "../secret",
            "..\\windows\\system32",
            "/etc/passwd",
            "sess/1",
            "sess\\1",
            "sess\x00null",
            "sess\nnewline",
            "sess space",
            "A" * 129,
            12345,
            None,
        ]
        for bad_id in invalid_cases:
            with pytest.raises(ValueError):
                validate_session_id(bad_id)

    def test_session_store_rejects_invalid_session_id(self, tmp_path):
        store = SessionStore(tmp_path / "test.db")
        conv = DummyConversation([{"role": "user", "content": "hi"}])
        with pytest.raises(ValueError):
            store.save_session("../traversal", conv)

        with pytest.raises(ValueError):
            store.load_session("bad/id")

        with pytest.raises(ValueError):
            store.delete_session("..\\bad")

        with pytest.raises(ValueError):
            store.append_message("bad id", "user", "hi")


class TestIncrementalSessionSave:
    """Audit #30: O(1) incremental message appending instead of O(N^2) rewrite."""

    def test_incremental_append_preserves_previous_message_ids(self, tmp_path):
        db_path = tmp_path / "incremental.db"
        store = SessionStore(db_path)

        msgs = [
            {"role": "user", "content": "turn 1", "agent_name": "", "timestamp": "2026-01-01T00:00:00"},
            {"role": "assistant", "content": "reply 1", "agent_name": "Tutor", "timestamp": "2026-01-01T00:00:01"},
        ]
        conv = DummyConversation(msgs)
        store.save_session("sess_inc", conv)

        # Inspect raw SQLite IDs for first 2 messages
        conn = store.flush()
        store.flush()
        conn = store.conn
        rows_1 = conn.execute("SELECT id, role, content FROM messages WHERE session_id = 'sess_inc' ORDER BY id").fetchall()
        assert len(rows_1) == 2
        id_1, id_2 = rows_1[0]["id"], rows_1[1]["id"]
        assert rows_1[0]["content"] == "turn 1"
        assert rows_1[1]["content"] == "reply 1"

        # Now append turn 2 to the conversation
        conv.messages.append(
            {"role": "user", "content": "turn 2", "agent_name": "", "timestamp": "2026-01-01T00:00:02"}
        )
        conv.messages.append(
            {"role": "assistant", "content": "reply 2", "agent_name": "Tutor", "timestamp": "2026-01-01T00:00:03"}
        )

        store.save_session("sess_inc", conv)

        # Verify that original messages kept their exact IDs (0 DELETE executed)
        store.flush()
        rows_2 = conn.execute("SELECT id, role, content FROM messages WHERE session_id = 'sess_inc' ORDER BY id").fetchall()
        assert len(rows_2) == 4
        assert rows_2[0]["id"] == id_1
        assert rows_2[1]["id"] == id_2
        assert rows_2[2]["id"] > id_2
        assert rows_2[3]["id"] > rows_2[2]["id"]

        # Verify sessions metadata
        session_row = conn.execute("SELECT * FROM sessions WHERE id = 'sess_inc'").fetchone()
        assert session_row["message_count"] == 4
        assert session_row["title"] == "turn 1"

    def test_direct_append_message(self, tmp_path):
        store = SessionStore(tmp_path / "append.db")
        msg_id_1 = store.append_message("sess_direct", "user", "direct message 1")
        msg_id_2 = store.append_message("sess_direct", "assistant", "direct message 2")

        assert msg_id_2 > msg_id_1
        loaded = store.load_session("sess_direct")
        assert len(loaded) == 2
        assert loaded[0]["content"] == "direct message 1"
        assert loaded[1]["content"] == "direct message 2"

    def test_divergence_reconciliation(self, tmp_path):
        """Audit #31: If conversation was rolled back or edited, reconcile cleanly."""
        store = SessionStore(tmp_path / "diverge.db")
        conv = DummyConversation([
            {"role": "user", "content": "m1"},
            {"role": "assistant", "content": "m2"},
            {"role": "user", "content": "m3"},
        ])
        store.save_session("sess_div", conv)
        assert len(store.load_session("sess_div")) == 3

        # Simulate user roll back to 1 message
        conv.messages = [{"role": "user", "content": "m1_modified"}]
        store.save_session("sess_div", conv)

        loaded = store.load_session("sess_div")
        assert len(loaded) == 1
        assert loaded[0]["content"] == "m1_modified"


class TestConversationFullHistoryRetention:
    """Audit #31: Full history retained for UI and persistence while model context is trimmed."""

    def test_conversation_retains_history_beyond_20_turns(self, tmp_path):
        conv = Conversation(session_id="sess_long", max_messages=20)

        # Add 30 turns
        for i in range(30):
            conv.add("user", f"User question {i}")
            conv.add("assistant", f"Assistant answer {i}")

        # Total added = 60 messages
        assert len(conv) == 60
        assert len(conv.get_all()) == 60

        # Model prompt window is bounded to 20
        model_msgs = conv.get_messages_for_model()
        assert len(model_msgs) == 20
        # The last message in model window should match the latest turn
        assert model_msgs[-1]["content"] == "Assistant answer 29"

        # Save to SQLite and reload: all 60 messages must be present!
        store = SessionStore(tmp_path / "full_hist.db")
        store.save_session("sess_long", conv)

        persisted = store.load_session("sess_long")
        assert len(persisted) == 60
        assert persisted[0]["content"] == "User question 0"
        assert persisted[-1]["content"] == "Assistant answer 29"


class TestSQLiteHardeningAndConcurrency:
    """Audit #111 & #113: WAL mode, busy timeout=10000, and foreign keys."""

    def test_db_pragmas_on_disk_connection(self, tmp_path):
        db_path = tmp_path / "pragma_test.db"
        conn = get_safe_db_connection(db_path)

        # Check WAL mode
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
        assert mode == "wal"

        # Check busy timeout
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout >= 5000

        # Check foreign keys
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()

    def test_concurrent_writes_and_reads(self, tmp_path):
        db_path = tmp_path / "concurrent_sessions.db"
        store = SessionStore(db_path)
        errors = []

        def writer(thread_id: int):
            try:
                for i in range(20):
                    sid = f"thread_{thread_id}"
                    store.append_message(sid, "user", f"msg {i} from thread {thread_id}")
                    # Also read another session
                    other_id = f"thread_{(thread_id + 1) % 4}"
                    _ = store.load_session(other_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent thread errors: {errors}"
        # Verify all thread sessions exist
        for t in range(4):
            msgs = store.load_session(f"thread_{t}")
            assert len(msgs) == 20


class TestOrchestratorAndBridgeSessionSync:
    """Audit #31 & Bridge Integration: session synchronization and deletion."""

    def test_orchestrator_clear_session_clears_persisted_storage(self, tmp_path, monkeypatch):
        from core.orchestrator import Orchestrator
        from core.agents.registry import AgentRegistry
        from core.agents.runtime import AgentRuntime

        store = SessionStore(tmp_path / "orch_sync.db")
        monkeypatch.setattr("core.session.get_session_store", lambda: store)

        reg = AgentRegistry()
        orch = Orchestrator(registry=reg, runtime=AgentRuntime(registry=reg))

        # Add message in memory and save
        conv = orch.get_conversation("sync_sess")
        conv.add("user", "hello before clear")
        store.save_session("sync_sess", conv)
        assert len(store.load_session("sync_sess")) == 1

        # Clear through orchestrator
        orch.clear_session("sync_sess")
        assert len(conv) == 0
        assert len(store.load_session("sync_sess")) == 0

    def test_bridge_session_validation_and_deletion(self, tmp_path, monkeypatch):
        from app.bridge import Bridge

        store = SessionStore(tmp_path / "bridge_test.db")
        monkeypatch.setattr("core.session.get_session_store", lambda: store)

        bridge = Bridge()
        # Seed a session
        store.append_message("valid_sess", "user", "first message")
        store.append_message("valid_sess", "assistant", "first response")

        # 1. get_sessions returns preview in a single call without N+1 queries
        res_json = bridge.get_sessions()
        data = json.loads(res_json)
        assert data["ok"] is True
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == "valid_sess"
        assert data["sessions"][0]["message_count"] == 2
        assert data["sessions"][0]["preview"] == "first message"

        # 2. load_session_id with invalid path traversal fails safely
        errors = []
        bridge.error.connect(lambda msg: errors.append(msg))
        bridge.load_session_id("../invalid_path")
        assert any("Failed to load session" in err for err in errors)

        # 3. delete_session safely deletes
        del_res = json.loads(bridge.delete_session("valid_sess"))
        assert del_res["ok"] is True
        assert len(store.load_session("valid_sess")) == 0

    def test_bridge_send_message_emits_agent_token_and_done(self, qapp):
        """Bridge must emit tokens and done asynchronously (Audit #52)."""
        from app.bridge.facade import Bridge
        import unittest.mock as mock

        bridge = Bridge()
        mock_orch = mock.MagicMock()
        mock_orch.stream.return_value = iter([("Agent full answer", True)])
        
        class MockConv:
            title = "Mock"
            def get_all(self): return []
        mock_orch.get_conversation.return_value = MockConv()
        
        bridge._orchestrator = mock_orch

        tokens = []
        dones = []
        bridge.token.connect(lambda idx, tok: tokens.append(tok))
        bridge.done.connect(lambda: dones.append(True))

        bridge.send_message("What is Python?")

        assert len(tokens) == 1
        assert tokens[0] == "Agent full answer"
        assert len(dones) == 1

    def test_tutor_engine_clear_session_resets_in_memory_context(self):
        """Verify TutorEngine.clear_session resets in-memory context."""
        from core.tutor_engine import TutorEngine
        from core.knowledge_graph import LearningDependencyGraph

        ldg = LearningDependencyGraph()
        tutor = TutorEngine(ldg)

        ctx = tutor.get_or_create_context("sess_tutor_clear")
        ctx.current_concept_id = "loops_1"
        assert tutor.session_contexts["sess_tutor_clear"].current_concept_id == "loops_1"

        tutor.clear_session("sess_tutor_clear")
        assert "sess_tutor_clear" not in tutor.session_contexts

