"""Gayatri AI — Per-session conversation history.

Maintains a rolling window of messages for each session.
Provides trimmed context for model input (respects token limits).
Thread-safe for single-user desktop use.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("gayatri.conversation")


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    agent_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Conversation:
    """Conversation history for one session.
    
    Retains full conversation history for UI and persistence (up to max_history turns),
    while get_messages_for_model() provides a trimmed rolling window bounded by max_messages
    for LLM prompt context.
    """
    session_id: str
    max_messages: int = 20
    max_history: int = 5000
    _messages: list[Message] = field(default_factory=list, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, role: str, content: str, agent_name: str = "") -> None:
        """Append a message to the conversation history."""
        with self._lock:
            self._messages.append(Message(role=role, content=content, agent_name=agent_name))
            if len(self._messages) > self.max_history:
                # Cap extremely large desktop sessions to max_history, preserving system messages
                system_msgs = [m for m in self._messages if m.role == "system"]
                other_msgs = [m for m in self._messages if m.role != "system"]
                num_keep = max(0, self.max_history - len(system_msgs))
                keep = other_msgs[-num_keep:] if num_keep > 0 else []
                self._messages = system_msgs + keep
            logger.debug(f"[{self.session_id}] +{role} ({len(self._messages)} msgs)")

    def get_messages_for_model(self, max_messages: int | None = None) -> list[dict]:
        """Return messages formatted for LLM input (list of {role, content}), trimmed to limit."""
        with self._lock:
            limit = max_messages or self.max_messages
            if len(self._messages) <= limit:
                return [{"role": m.role, "content": m.content} for m in self._messages]

            # Preserve system messages, take recent turns up to limit
            system_msgs = [m for m in self._messages if m.role == "system"]
            other_msgs = [m for m in self._messages if m.role != "system"]
            num_keep = max(0, limit - len(system_msgs))
            keep = other_msgs[-num_keep:] if num_keep > 0 else []
            return [{"role": m.role, "content": m.content} for m in (system_msgs + keep)]

    def get_recent(self, n: int = 5) -> list[Message]:
        """Return the last n messages."""
        with self._lock:
            return list(self._messages[-n:])

    def clear(self) -> None:
        """Clear all messages."""
        with self._lock:
            self._messages.clear()
            logger.info(f"[{self.session_id}] Conversation cleared")

    def get_all(self) -> list[dict]:
        """Return all messages as dicts (for persistence/UI)."""
        with self._lock:
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "agent_name": m.agent_name,
                    "timestamp": m.timestamp,
                }
                for m in self._messages
            ]

    def __len__(self) -> int:
        with self._lock:
            return len(self._messages)


class ConversationStore:
    """Manages conversations for all active sessions.

    Usage:
        store = ConversationStore()
        conv = store.get("session-1")
        conv.add("user", "Hello")
        conv.add("assistant", "Hi there!")
        msgs = conv.get_messages_for_model()  # for model input
    """

    def __init__(self):
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str) -> Conversation:
        """Get or create a conversation for the session."""
        with self._lock:
            if session_id not in self._conversations:
                self._conversations[session_id] = Conversation(session_id=session_id)
            return self._conversations[session_id]

    def new_session(self, session_id: str) -> Conversation:
        """Create a fresh conversation (clears any existing one)."""
        with self._lock:
            self._conversations[session_id] = Conversation(session_id=session_id)
            logger.info(f"New session: {session_id}")
            return self._conversations[session_id]

    def delete(self, session_id: str) -> None:
        """Remove a conversation."""
        with self._lock:
            self._conversations.pop(session_id, None)

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        with self._lock:
            return list(self._conversations.keys())
