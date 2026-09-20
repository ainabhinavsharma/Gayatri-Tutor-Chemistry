"""Tests for Phase 14: Database & Schema Resilience Re-Audit (P14-T01 to P14-T05)."""
import sqlite3
import pytest
from core.db import (
    get_safe_db_connection,
    run_migrations,
    get_last_recovery_event,
    get_all_recovery_events,
    clear_recovery_events,
)


def test_safe_db_connection_pragmas(tmp_path):
    """Test safe SQLite connection initialization with WAL and PRAGMAs."""
    db_path = tmp_path / "test_safe.db"
    conn = get_safe_db_connection(db_path)

    try:
        # Check journal mode is WAL
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() == "wal"

        # Check foreign keys enabled
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1
    finally:
        conn.close()


def test_corrupt_database_recovery(tmp_path):
    """Test corrupt database detection, backing up, and creating fresh DB."""
    clear_recovery_events()

    corrupt_db_path = tmp_path / "test_corrupt.db"

    # Create a corrupt file containing invalid garbage text
    with open(corrupt_db_path, "wb") as f:
        f.write(b"NOT_A_VALID_SQLITE_HEADER_GARBAGE_BYTES_0123456789")

    # Access via get_safe_db_connection
    conn = get_safe_db_connection(corrupt_db_path)
    try:
        # Check that connection works on a fresh DB
        result = conn.execute("PRAGMA quick_check;").fetchone()[0]
        assert result == "ok"
    finally:
        conn.close()

    # Verify recovery event was recorded
    last_event = get_last_recovery_event()
    assert last_event is not None
    assert last_event["original_path"] == str(corrupt_db_path)
    assert ".corrupt-" in last_event["backup_path"]
    assert "Your previous database appears corrupted" in last_event["user_message"]


def test_incremental_schema_migrations(tmp_path):
    """Test incremental schema migrations using PRAGMA user_version."""
    db_path = tmp_path / "test_migrations.db"
    conn = get_safe_db_connection(db_path)

    try:
        def m1(c):
            c.execute("CREATE TABLE t1 (id INTEGER PRIMARY KEY);")

        def m2(c):
            c.execute("CREATE TABLE t2 (name TEXT);")

        migrations = {
            1: ("create_t1", m1),
            2: ("create_t2", m2),
        }

        # Apply migrations
        cur_v = run_migrations(conn, migrations)
        assert cur_v == 2

        # Check user_version PRAGMA
        v = conn.execute("PRAGMA user_version;").fetchone()[0]
        assert v == 2

        # Check _schema_migrations tracking table
        rows = conn.execute("SELECT version, name FROM _schema_migrations ORDER BY version").fetchall()
        assert len(rows) == 2
        assert rows[0]["version"] == 1
        assert rows[0]["name"] == "create_t1"
        assert rows[1]["version"] == 2
        assert rows[1]["name"] == "create_t2"

        # Re-running migrations is idempotent
        cur_v_2 = run_migrations(conn, migrations)
        assert cur_v_2 == 2
    finally:
        conn.close()
