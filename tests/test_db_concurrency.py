"""Tests for DB-002 (corruption event notification), DB-003 (schema migrations), and DB-004 (concurrency)."""

import sqlite3
import threading
from pathlib import Path

from core.db import (
    get_safe_db_connection,
    get_last_recovery_event,
    clear_recovery_events,
    run_migrations,
)


def test_db_corruption_recovery_event_recorded(tmp_path: Path):
    """DB-002: Verify corruption recovery event is captured and readable."""
    clear_recovery_events()
    corrupt_db_path = tmp_path / "corrupt_test.db"

    # Write corrupt garbage into the file
    corrupt_db_path.write_text("THIS_IS_NOT_A_VALID_SQLITE_FILE_CONTENT", encoding="utf-8")

    # Connect should detect corruption, back up the file, and record an event
    conn = get_safe_db_connection(corrupt_db_path)
    conn.close()

    event = get_last_recovery_event()
    assert event is not None
    assert "corrupt_test" in event["original_path"]
    assert Path(event["backup_path"]).exists()
    assert "user_message" in event
    assert "backup was safely preserved" in event["user_message"]


def test_db_schema_migrations_applied_and_tracked(tmp_path: Path):
    """DB-003: Verify incremental migrations update PRAGMA user_version and history."""
    db_path = tmp_path / "mig_test.db"
    conn = sqlite3.connect(str(db_path))

    migrations = {
        1: ("create_users_table", lambda c: c.execute("CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT);")),
        2: ("add_email_column", lambda c: c.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT '';")),
    }

    v = run_migrations(conn, migrations)
    assert v == 2

    # Check PRAGMA user_version
    cur_v = conn.execute("PRAGMA user_version;").fetchone()[0]
    assert cur_v == 2

    # Verify columns exist
    conn.execute("INSERT INTO users (id, name, email) VALUES ('u1', 'Alice', 'alice@example.com');")
    row = conn.execute("SELECT * FROM users WHERE id='u1';").fetchone()
    assert row[1] == "Alice"
    assert row[2] == "alice@example.com"

    # Re-running migrations is an idempotent no-op
    v2 = run_migrations(conn, migrations)
    assert v2 == 2

    conn.close()


def test_db_concurrency_multi_threaded_writes(tmp_path: Path):
    """DB-004: Validate SQLite concurrency under WAL mode with multiple threads writing simultaneously."""
    db_path = tmp_path / "concurrency_test.db"

    # Initialize table with get_safe_db_connection (which sets WAL, busy_timeout)
    conn_init = get_safe_db_connection(db_path)
    conn_init.execute("CREATE TABLE counter (thread_id INT PRIMARY KEY, count INT);")
    conn_init.commit()
    conn_init.close()

    errors: list[Exception] = []
    num_threads = 8
    iterations_per_thread = 50

    def worker(tid: int):
        try:
            for i in range(iterations_per_thread):
                conn = get_safe_db_connection(db_path)
                with conn:
                    conn.execute(
                        "INSERT INTO counter (thread_id, count) VALUES (?, ?) "
                        "ON CONFLICT(thread_id) DO UPDATE SET count = count + 1;",
                        (tid, 1),
                    )
                conn.close()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrency errors encountered: {errors}"

    conn_check = get_safe_db_connection(db_path)
    rows = conn_check.execute("SELECT COUNT(*), SUM(count) FROM counter;").fetchone()
    conn_check.close()

    assert rows[0] == num_threads
    assert rows[1] == num_threads * iterations_per_thread
