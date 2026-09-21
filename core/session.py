"""Gayatri AI — SQLite-backed session persistence.

Stores and retrieves conversation sessions.
Schema: sessions (metadata), messages (full history).
Uses the DB_PATH configured in core.config.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("gayatri.session")

from core.security.validation import validate_session_id


class SessionStore:
    """SQLite-backed session persistence.

    Tables:
        sessions: id, title, created_at, updated_at, message_count
        messages: id, session_id, role, content, agent_name, timestamp
    """

    def __init__(self, db_path: str | Path | None = None):
        from core.config import DB_PATH
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db_conn: sqlite3.Connection | None = None
        self._create_schema()
        
        # Async Write Queue (Phase 3 Optimization)
        import queue
        self._write_queue = queue.Queue()
        self._shutdown_event = threading.Event()
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True, name="Gayatri-DBWriter")
        self._writer_thread.start()

    def _writer_loop(self):
        """Background thread consuming the async DB write queue."""
        while not self._shutdown_event.is_set() or not self._write_queue.empty():
            try:
                task = self._write_queue.get(timeout=0.1)
                func, args, kwargs = task
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Async DB write failed: {e}")
                self._write_queue.task_done()
            except queue.Empty:
                pass
                
    def flush(self):
        """Block until all pending async writes are written to disk."""
        self._write_queue.join()

    def shutdown(self):
        """Gracefully shutdown the DB writer thread."""
        self._shutdown_event.set()
        if self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)
            
    def _enqueue_write(self, func, *args, **kwargs):
        """Put a DB write task onto the background queue."""
        self._write_queue.put((func, args, kwargs))

    @property
    def conn(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        with self._lock:
            if self._db_conn is None:
                from core.db import get_safe_db_connection
                self._db_conn = get_safe_db_connection(self.db_path)
            return self._db_conn

    def _create_schema(self) -> None:
        """Create or migrate tables."""
        from core.db import run_migrations
        conn = self.conn
        
        def initial_schema(c):
            c.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id          TEXT PRIMARY KEY,
                    profile_id  TEXT DEFAULT 'default',
                    title       TEXT DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    agent_name  TEXT DEFAULT '',
                    timestamp   TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

                CREATE TABLE IF NOT EXISTS tutor_contexts (
                    session_id              TEXT PRIMARY KEY,
                    state_json              TEXT NOT NULL DEFAULT '{}',
                    current_concept_id      TEXT DEFAULT '',
                    current_concept_name    TEXT DEFAULT '',
                    concept_description     TEXT DEFAULT '',
                    subject                 TEXT DEFAULT '',
                    mastery                 REAL DEFAULT 0.0,
                    waiting_for_answer      INTEGER DEFAULT 0,
                    last_response_type      TEXT DEFAULT '',
                    last_attempt_correct    INTEGER DEFAULT 0,
                    updated_at              TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
            """)

        def add_mode_and_user_id(c):
            try:
                c.execute("ALTER TABLE sessions ADD COLUMN mode TEXT DEFAULT 'general_assistant';")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT DEFAULT 'local_user_1';")
            except Exception:
                pass
            c.execute("UPDATE sessions SET mode = 'general_assistant' WHERE mode IS NULL;")
            c.execute("UPDATE sessions SET user_id = 'local_user_1' WHERE user_id IS NULL;")
        
        def add_tutor_context_columns_and_profile_id(c):
            """Migration 3: patch DBs that pre-date the full tutor_contexts schema."""
            for col, defn in [
                ("current_concept_id",   "TEXT DEFAULT ''"),
                ("current_concept_name",  "TEXT DEFAULT ''"),
                ("concept_description",   "TEXT DEFAULT ''"),
                ("subject",               "TEXT DEFAULT ''"),
                ("mastery",               "REAL DEFAULT 0.0"),
                ("waiting_for_answer",    "INTEGER DEFAULT 0"),
                ("last_response_type",    "TEXT DEFAULT ''"),
                ("last_attempt_correct",  "INTEGER DEFAULT 0"),
                ("state_json",            "TEXT DEFAULT '{}'"),
            ]:
                try:
                    c.execute(f"ALTER TABLE tutor_contexts ADD COLUMN {col} {defn};")
                except Exception:
                    pass  # column already exists
            # Ensure sessions has profile_id (may be missing in truly old DBs)
            try:
                c.execute("ALTER TABLE sessions ADD COLUMN profile_id TEXT DEFAULT 'default';")
            except Exception:
                pass

        migrations = {
            1: ("initial_schema", initial_schema),
            2: ("add_mode_and_user_id", add_mode_and_user_id),
            3: ("add_tutor_context_columns_and_profile_id", add_tutor_context_columns_and_profile_id),
        }
        
        run_migrations(conn, migrations)

            
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT DEFAULT '';")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Already present
            
        logger.info(f"Session DB ready: {self.db_path}")

    def save_session(self, session_id: str, conversation: Any, tutor_context: Any = None) -> None:
        """Queue a session for async background saving (Audit #28)."""
        session_id = validate_session_id(session_id)
        
        # Deepcopy the state we need before queueing it to avoid race conditions!
        title = getattr(conversation, "title", "New Chat")
        messages = list(conversation.get_all()) if hasattr(conversation, "get_all") else list(conversation)
        
        mode = getattr(conversation, "mode", "general_assistant")
        user_id = getattr(conversation, "user_id", "local_user_1")
        self._enqueue_write(
            self._save_session_internal,
            session_id, title, messages, tutor_context, mode, user_id
        )

    def _save_session_internal(self, session_id: str, title: str, messages: list[dict], tutor_context: Any = None, mode: str = "general_assistant", user_id: str = "local_user_1") -> None:
        """Synchronously persist the conversation to SQLite."""
        with self._lock:
            conn = self.conn
            now = datetime.now().isoformat()
            n_msgs = len(messages)
            first_preview = messages[0]["content"][:80] if messages else ""

            # 1. Ensure parent session record exists first to satisfy FOREIGN KEY constraint
            with conn:
                conn.execute(
                    """INSERT INTO sessions (id, title, created_at, updated_at, message_count, mode, user_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                           title = CASE WHEN sessions.title IS NULL OR sessions.title = '' THEN excluded.title ELSE sessions.title END,
                           updated_at = excluded.updated_at,
                           message_count = excluded.message_count,
                           mode = excluded.mode,
                           user_id = excluded.user_id""",
                    (session_id, first_preview, now, now, n_msgs, mode, user_id),
                )

                # 2. Check existing message count and latest message for incremental append (Audit #30)
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM messages WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                db_count = row["cnt"] if row else 0

                is_incremental = False
                if 0 < db_count <= n_msgs:
                    last_db = conn.execute(
                        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                        (session_id,),
                    ).fetchone()
                    if (
                        last_db
                        and last_db["role"] == messages[db_count - 1]["role"]
                        and last_db["content"] == messages[db_count - 1]["content"]
                    ):
                        is_incremental = True

                if is_incremental:
                    # Incremental append: insert only messages[db_count:] without deleting anything (Audit #30)
                    new_slice = messages[db_count:]
                    if new_slice:
                        conn.executemany(
                            "INSERT INTO messages (session_id, role, content, agent_name, timestamp) "
                            "VALUES (?, ?, ?, ?, ?)",
                            [
                                (
                                    session_id,
                                    m["role"],
                                    m["content"],
                                    m.get("agent_name", ""),
                                    m.get("timestamp", now),
                                )
                                for m in new_slice
                            ],
                        )
                elif db_count == 0:
                    # Brand new session: insert all messages in bulk
                    if messages:
                        conn.executemany(
                            "INSERT INTO messages (session_id, role, content, agent_name, timestamp) "
                            "VALUES (?, ?, ?, ?, ?)",
                            [
                                (
                                    session_id,
                                    m["role"],
                                    m["content"],
                                    m.get("agent_name", ""),
                                    m.get("timestamp", now),
                                )
                                for m in messages
                            ],
                        )
                else:
                    # History diverged or session was cleared/rolled back (Audit #31)
                    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                    if messages:
                        conn.executemany(
                            "INSERT INTO messages (session_id, role, content, agent_name, timestamp) "
                            "VALUES (?, ?, ?, ?, ?)",
                            [
                                (
                                    session_id,
                                    m["role"],
                                    m["content"],
                                    m.get("agent_name", ""),
                                    m.get("timestamp", now),
                                )
                                for m in messages
                            ],
                        )

            logger.debug(f"Saved session {session_id}: {n_msgs} messages (db had {db_count}, incremental={is_incremental})")

            if tutor_context is not None:
                self.save_tutor_context(session_id, tutor_context)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: str = "",
        timestamp: str | None = None,
    ) -> int:
        """Directly append a single message in O(1) to the session store (Audit #30)."""
        session_id = validate_session_id(session_id)
        with self._lock:
            conn = self.conn
            now = timestamp or datetime.now().isoformat()

            # Ensure parent session record exists first to satisfy foreign keys
            with conn:
                conn.execute(
                    """INSERT INTO sessions (id, title, created_at, updated_at, message_count)
                       VALUES (?, ?, ?, ?, 0)
                       ON CONFLICT(id) DO UPDATE SET
                           title = CASE WHEN sessions.title IS NULL OR sessions.title = '' THEN excluded.title ELSE sessions.title END,
                           updated_at = excluded.updated_at""",
                    (session_id, content[:80], now, now),
                )

                cursor = conn.execute(
                    "INSERT INTO messages (session_id, role, content, agent_name, timestamp) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (session_id, role, content, agent_name, now),
                )
                msg_id = cursor.lastrowid

                conn.execute(
                    "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
                    (session_id,),
                )
            return msg_id

    def clear_session_messages(self, session_id: str) -> None:
        """Clear all messages and tutor context for a session while retaining session entry (Audit #31)."""
        session_id = validate_session_id(session_id)
        with self._lock:
            conn = self.conn
            now = datetime.now().isoformat()
            with conn:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM tutor_contexts WHERE session_id = ?", (session_id,))
                conn.execute(
                    "UPDATE sessions SET message_count = 0, title = '', updated_at = ? WHERE id = ?",
                    (now, session_id),
                )
            logger.info(f"Cleared messages for session: {session_id}")

    def save_tutor_context(self, session_id: str, ctx: Any) -> None:
        """Save tutor teaching state for a session."""
        session_id = validate_session_id(session_id)
        if not ctx:
            return
        with self._lock:
            conn = self.conn
            now = datetime.now().isoformat()

            waiting = 1 if getattr(ctx, "waiting_for_answer", False) else 0
            last_correct = getattr(ctx, "last_attempt_correct", None)
            if last_correct is True:
                last_correct_int = 1
            elif last_correct is False:
                last_correct_int = 0
            else:
                last_correct_int = None

            with conn:
                # Ensure parent session record exists first to satisfy foreign keys
                conn.execute(
                    """INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at, message_count)
                       VALUES (?, ?, ?, ?, 0)""",
                    (session_id, "New Session", now, now),
                )
                conn.execute(
                    """INSERT INTO tutor_contexts (
                           session_id, current_concept_id, current_concept_name,
                           concept_description, subject, mastery, waiting_for_answer,
                           last_response_type, last_attempt_correct, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(session_id) DO UPDATE SET
                           current_concept_id = excluded.current_concept_id,
                           current_concept_name = excluded.current_concept_name,
                           concept_description = excluded.concept_description,
                           subject = excluded.subject,
                           mastery = excluded.mastery,
                           waiting_for_answer = excluded.waiting_for_answer,
                           last_response_type = excluded.last_response_type,
                           last_attempt_correct = excluded.last_attempt_correct,
                           updated_at = excluded.updated_at""",
                    (
                        session_id,
                        getattr(ctx, "current_concept_id", ""),
                        getattr(ctx, "current_concept_name", ""),
                        getattr(ctx, "concept_description", ""),
                        getattr(ctx, "subject", ""),
                        float(getattr(ctx, "mastery", 0.3)),
                        waiting,
                        getattr(ctx, "last_response_type", "explain"),
                        last_correct_int,
                        now,
                    ),
                )
            logger.debug(f"Saved tutor context for session {session_id}")

    def load_tutor_context(self, session_id: str) -> Any:
        """Load tutor context for a session."""
        session_id = validate_session_id(session_id)
        self.flush()
        with self._lock:
            conn = self.conn
            row = conn.execute(
                """SELECT current_concept_id, current_concept_name, concept_description,
                          subject, mastery, waiting_for_answer, last_response_type,
                          last_attempt_correct, updated_at
                   FROM tutor_contexts WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
            if not row:
                return None

            from core.tutor_engine import TutorContext
            last_correct = None
            if row["last_attempt_correct"] == 1:
                last_correct = True
            elif row["last_attempt_correct"] == 0:
                last_correct = False

            last_interaction = 0.0
            if "updated_at" in row.keys() and row["updated_at"]:
                try:
                    last_interaction = datetime.fromisoformat(row["updated_at"]).timestamp()
                except Exception:
                    logger.debug("Failed to parse updated_at timestamp, defaulting to 0.0", exc_info=True)

            return TutorContext(
                current_concept_id=row["current_concept_id"] or "",
                current_concept_name=row["current_concept_name"] or "",
                concept_description=row["concept_description"] or "",
                subject=row["subject"] or "",
                mastery=float(row["mastery"] or 0.3),
                waiting_for_answer=bool(row["waiting_for_answer"]),
                last_response_type=row["last_response_type"] or "explain",
                last_attempt_correct=last_correct,
                last_interaction_time=last_interaction,
            )

    def load_session(self, session_id: str) -> list[dict]:
        """Load all messages for a session.

        Returns:
            List of message dicts {role, content, agent_name, timestamp}
        """
        session_id = validate_session_id(session_id)
        self.flush()
        with self._lock:
            conn = self.conn
            cursor = conn.execute(
                "SELECT role, content, agent_name, timestamp FROM messages "
                "WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
            return [
                {
                    "role": row["role"],
                    "content": row["content"],
                    "agent_name": row["agent_name"],
                    "timestamp": row["timestamp"],
                }
                for row in cursor.fetchall()
            ]

    def list_sessions(
        self,
        mode: str | None = None,
        user_id: str | None = None,
        profile_id: str | None = None,
    ) -> list[dict]:
        """List sessions ordered by most recent first, optionally filtered by mode, user_id, or profile_id.

        Returns:
            List of {id, profile_id, title, mode, user_id, created_at, updated_at, message_count, preview}
        """
        self.flush()
        with self._lock:
            conn = self.conn
            query = "SELECT id, profile_id, title, mode, user_id, created_at, updated_at, message_count FROM sessions WHERE 1=1"
            params = []
            if mode is not None:
                query += " AND mode = ?"
                params.append(mode)
            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)
            if profile_id is not None:
                query += " AND profile_id = ?"
                params.append(profile_id)

            query += " ORDER BY updated_at DESC"
            cursor = conn.execute(query, params)

            return [
                {
                    "id": row["id"],
                    "profile_id": row["profile_id"] if "profile_id" in row.keys() else "default",
                    "title": row["title"] or row["id"][:20],
                    "mode": row["mode"] if "mode" in row.keys() else "general_assistant",
                    "user_id": row["user_id"] if "user_id" in row.keys() else "local_user_1",
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"],
                    "preview": row["title"] or "",
                }
                for row in cursor.fetchall()
            ]

    def delete_session(self, session_id: str) -> None:
        """Delete a session, its messages, and its tutor context."""
        session_id = validate_session_id(session_id)
        self._enqueue_write(self._delete_session_internal, session_id)
        
    def _delete_session_internal(self, session_id: str) -> None:
        with self._lock:
            conn = self.conn
            with conn:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM tutor_contexts WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            logger.info(f"Deleted session: {session_id}")

    def get_session_count(self) -> int:
        """Return total number of saved sessions."""
        with self._lock:
            conn = self.conn
            row = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
            return row[0]

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            if self._db_conn:
                self._db_conn.close()
                self._db_conn = None


# Global session store instance
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the global session store (singleton)."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store


__all__ = [
    "SessionStore",
    "get_session_store",
    "validate_session_id",
]
