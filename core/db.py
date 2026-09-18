"""Gayatri AI — Safe Database Access.

Provides a safe way to get an SQLite connection, handling corrupt databases
by backing them up and creating a fresh one.
"""

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger("gayatri.db")

_RECOVERY_EVENTS: list[dict] = []


@dataclass
class CorruptionRecoveryEvent:
    timestamp: str
    original_path: str
    backup_path: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "original_path": self.original_path,
            "backup_path": self.backup_path,
            "reason": self.reason,
            "user_message": (
                f"Your previous database appears corrupted. A backup was safely preserved at: {self.backup_path}"
            ),
        }


def get_last_recovery_event() -> dict | None:
    """Return the most recent corruption recovery event, if any (Audit #DB-002)."""
    return _RECOVERY_EVENTS[-1] if _RECOVERY_EVENTS else None


def get_all_recovery_events() -> list[dict]:
    """Return all recorded corruption recovery events."""
    return list(_RECOVERY_EVENTS)


def clear_recovery_events() -> None:
    """Clear recovery event log."""
    _RECOVERY_EVENTS.clear()


def get_safe_db_connection(db_path: Path | str) -> sqlite3.Connection:
    """Get a safe SQLite connection, handling corrupt databases by backing them up."""
    is_memory = str(db_path) == ":memory:"

    if not is_memory:
        db_path = Path(db_path)
        if db_path.exists() and db_path.stat().st_size > 0:
            try:
                conn = sqlite3.connect(str(db_path))
                try:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA quick_check")
                    result = cursor.fetchone()
                    if not result or result[0] != "ok":
                        raise sqlite3.DatabaseError("PRAGMA quick_check failed")
                finally:
                    conn.close()
            except sqlite3.DatabaseError as e:
                logger.warning(f"Database {db_path} is corrupt: {e}. Backing up and recreating.")
                now_str = datetime.now().strftime('%Y%m%d-%H%M%S')
                backup_path = db_path.with_name(f"{db_path.stem}.corrupt-{now_str}{db_path.suffix}")
                try:
                    shutil.move(str(db_path), str(backup_path))
                    logger.info(f"Corrupt database backed up to {backup_path}")
                    event = CorruptionRecoveryEvent(
                        timestamp=datetime.now().isoformat(),
                        original_path=str(db_path),
                        backup_path=str(backup_path),
                        reason=str(e),
                    )
                    _RECOVERY_EVENTS.append(event.to_dict())
                except Exception as move_err:
                    logger.error(f"Failed to backup corrupt database: {move_err}")
                    try:
                        db_path.unlink(missing_ok=True)
                    except Exception as unlink_err:
                        logger.error(f"Failed to delete corrupt database: {unlink_err}")
                        raise sqlite3.DatabaseError(f"Database is corrupt and cannot be backed up or deleted: {unlink_err}")

        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        if not is_memory:
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception as exc:
        logger.warning(f"Could not apply database PRAGMAs: {exc}")
    return conn


def run_migrations(
    conn: sqlite3.Connection,
    migrations: dict[int, tuple[str, Callable[[sqlite3.Connection], None]]],
) -> int:
    """Run incremental SQLite schema migrations using PRAGMA user_version (Audit #DB-003).

    Args:
        conn: SQLite connection.
        migrations: Map of target_version -> (migration_name, callable(conn)).

    Returns:
        The current schema version after migrations.
    """
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """
        )

        cur_version = conn.execute("PRAGMA user_version;").fetchone()[0]
        logger.debug(f"Current database schema version: {cur_version}")

        sorted_versions = sorted(v for v in migrations if v > cur_version)
        for v in sorted_versions:
            name, fn = migrations[v]
            logger.info(f"Applying schema migration {v}: {name}")
            fn(conn)
            conn.execute(
                "INSERT OR REPLACE INTO _schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                (v, name, datetime.now().isoformat()),
            )
            conn.execute(f"PRAGMA user_version = {v};")
            cur_version = v

        return cur_version

