"""Gayatri AI — Multi-User Profile Architecture.

Provides thread-safe, SQLite-backed management of local user profiles
(students, teachers, parents) with isolated learning sessions and curriculum progress.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.db import get_safe_db_connection

logger = logging.getLogger("gayatri.profile")

DEFAULT_PROFILE_ID = "default"


@dataclass
class UserProfile:
    """User profile entity representing a learner, teacher, or parent."""
    id: str
    username: str
    display_name: str
    grade: str = "Grade 9"
    board: str = "CBSE"
    role: str = "student"  # student, teacher, parent
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "grade": self.grade,
            "board": self.board,
            "role": self.role,
            "created_at": self.created_at,
            "settings": self.settings,
        }


class ProfileManager:
    """Thread-safe manager for user profiles stored in SQLite."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            from core.config import DB_PATH
            self.db_path = Path(DB_PATH)
        else:
            self.db_path = Path(db_path)

        self._lock = threading.RLock()
        self._active_profile_id = DEFAULT_PROFILE_ID
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return get_safe_db_connection(self.db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        display_name TEXT NOT NULL,
                        grade TEXT NOT NULL DEFAULT 'Grade 9',
                        board TEXT NOT NULL DEFAULT 'CBSE',
                        role TEXT NOT NULL DEFAULT 'student',
                        created_at TEXT NOT NULL,
                        settings_json TEXT NOT NULL DEFAULT '{}'
                    );
                    """
                )
                # Seed default profile if not present
                cur = conn.execute("SELECT id FROM user_profiles WHERE id = ?;", (DEFAULT_PROFILE_ID,))
                if not cur.fetchone():
                    conn.execute(
                        """
                        INSERT INTO user_profiles (id, username, display_name, grade, board, role, created_at, settings_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            DEFAULT_PROFILE_ID,
                            "default_user",
                            "Default Learner",
                            "Grade 9",
                            "CBSE",
                            "student",
                            datetime.now().isoformat(),
                            "{}",
                        ),
                    )
            conn.close()

    def create_profile(
        self,
        username: str,
        display_name: str,
        grade: str = "Grade 9",
        board: str = "CBSE",
        role: str = "student",
        settings: dict[str, Any] | None = None,
    ) -> UserProfile:
        """Create and store a new user profile."""
        import uuid
        profile_id = f"user_{uuid.uuid4().hex[:12]}"
        settings_dict = settings or {}
        now = datetime.now().isoformat()

        with self._lock:
            conn = self._get_conn()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO user_profiles (id, username, display_name, grade, board, role, created_at, settings_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            profile_id,
                            username.strip().lower(),
                            display_name.strip(),
                            grade,
                            board,
                            role,
                            now,
                            json.dumps(settings_dict),
                        ),
                    )
            finally:
                conn.close()

        profile = UserProfile(
            id=profile_id,
            username=username.strip().lower(),
            display_name=display_name.strip(),
            grade=grade,
            board=board,
            role=role,
            created_at=now,
            settings=settings_dict,
        )
        logger.info(f"Created profile {profile.username} ({profile.id})")
        return profile

    def get_profile(self, profile_id: str) -> UserProfile | None:
        """Retrieve a profile by ID."""
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT id, username, display_name, grade, board, role, created_at, settings_json "
                    "FROM user_profiles WHERE id = ?;",
                    (profile_id,),
                ).fetchone()
                if not row:
                    return None
                return UserProfile(
                    id=row["id"],
                    username=row["username"],
                    display_name=row["display_name"],
                    grade=row["grade"],
                    board=row["board"],
                    role=row["role"],
                    created_at=row["created_at"],
                    settings=json.loads(row["settings_json"] or "{}"),
                )
            finally:
                conn.close()

    def list_profiles(self) -> list[UserProfile]:
        """List all registered profiles."""
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT id, username, display_name, grade, board, role, created_at, settings_json "
                    "FROM user_profiles ORDER BY created_at ASC;"
                ).fetchall()
                profiles = []
                for row in rows:
                    profiles.append(
                        UserProfile(
                            id=row["id"],
                            username=row["username"],
                            display_name=row["display_name"],
                            grade=row["grade"],
                            board=row["board"],
                            role=row["role"],
                            created_at=row["created_at"],
                            settings=json.loads(row["settings_json"] or "{}"),
                        )
                    )
                return profiles
            finally:
                conn.close()

    def switch_profile(self, profile_id: str) -> UserProfile:
        """Switch active profile for the current application session."""
        with self._lock:
            profile = self.get_profile(profile_id)
            if not profile:
                raise ValueError(f"Profile '{profile_id}' does not exist.")
            self._active_profile_id = profile_id
            logger.info(f"Switched active profile to {profile.username} ({profile.id})")
            return profile

    def get_active_profile(self) -> UserProfile:
        """Return the currently active user profile."""
        with self._lock:
            profile = self.get_profile(self._active_profile_id)
            if not profile:
                profile = self.get_profile(DEFAULT_PROFILE_ID)
                if not profile:
                    raise RuntimeError("No user profiles available, including default.")
                self._active_profile_id = DEFAULT_PROFILE_ID
            return profile


_GLOBAL_PROFILE_MANAGER: ProfileManager | None = None
_PM_LOCK = threading.Lock()


def get_profile_manager() -> ProfileManager:
    """Singleton getter for the global ProfileManager."""
    global _GLOBAL_PROFILE_MANAGER
    with _PM_LOCK:
        if _GLOBAL_PROFILE_MANAGER is None:
            _GLOBAL_PROFILE_MANAGER = ProfileManager()
        return _GLOBAL_PROFILE_MANAGER
