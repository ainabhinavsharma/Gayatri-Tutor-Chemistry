import re

with open('core/session.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace save_session
content = re.sub(
    r'def save_session\(self, session_id: str, conversation: Any, tutor_context: Any = None\) -> None:.*?def _save_session_internal',
    '''def save_session(self, session_id: str, conversation: Any, tutor_context: Any = None, mode: str = "general_assistant", user_id: str = "local_user_1") -> None:
        """Queue a session for async background saving (Audit #28)."""
        session_id = validate_session_id(session_id)
        
        # Deepcopy the state we need before queueing it to avoid race conditions!
        title = getattr(conversation, "title", "New Chat")
        messages = list(conversation.get_all()) if hasattr(conversation, "get_all") else list(conversation)
        
        self._enqueue_write(
            self._save_session_internal,
            session_id, title, messages, tutor_context, mode, user_id
        )

    def _save_session_internal''',
    content,
    flags=re.DOTALL
)

# Replace _save_session_internal
content = re.sub(
    r'def _save_session_internal\(self, session_id: str, title: str, messages: list\[dict\], tutor_context: Any = None\) -> None:.*?\(session_id, first_preview, now, now, n_msgs\),\s*\)',
    '''def _save_session_internal(self, session_id: str, title: str, messages: list[dict], tutor_context: Any = None, mode: str = "general_assistant", user_id: str = "local_user_1") -> None:
        """Synchronously persist the conversation to SQLite."""
        with self._lock:
            conn = self.conn
            now = datetime.now().isoformat()
            n_msgs = len(messages)
            first_preview = messages[0]["content"][:80] if messages else ""

            # 1. Ensure parent session record exists first to satisfy FOREIGN KEY constraint
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
            )''',
    content,
    flags=re.DOTALL
)

# Replace list_sessions
content = re.sub(
    r'def list_sessions\(self, profile_id: str \| None = None\) -> list\[dict\]:.*?return result',
    '''def list_sessions(self, profile_id: str | None = None, mode: str | None = None, user_id: str | None = None) -> list[dict]:
        """List all sessions ordered by most recent first, optionally filtered by profile, mode, and user_id.

        Returns:
            List of {id, profile_id, title, created_at, updated_at, message_count, preview, mode, user_id}
        """
        self.flush()
        with self._lock:
            conn = self.conn
            
            query = "SELECT id, profile_id, title, created_at, updated_at, message_count, mode, user_id FROM sessions"
            conditions = []
            params = []
            
            if profile_id is not None:
                conditions.append("profile_id = ?")
                params.append(profile_id)
            if mode is not None:
                conditions.append("mode = ?")
                params.append(mode)
            if user_id is not None:
                conditions.append("user_id = ?")
                params.append(user_id)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += " ORDER BY updated_at DESC"
            
            cursor = conn.execute(query, tuple(params))
            
            result = []
            for row in cursor:
                result.append(
                    {
                        "id": row["id"],
                        "profile_id": row["profile_id"] if "profile_id" in row.keys() else "default",
                        "title": row["title"] or row["id"][:20],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "message_count": row["message_count"],
                        "preview": row["title"] or "New Session",
                        "mode": row["mode"] if "mode" in row.keys() else "general_assistant",
                        "user_id": row["user_id"] if "user_id" in row.keys() else "local_user_1",
                    }
                )
            return result''',
    content,
    flags=re.DOTALL
)

with open('core/session.py', 'w', encoding='utf-8') as f:
    f.write(content)
