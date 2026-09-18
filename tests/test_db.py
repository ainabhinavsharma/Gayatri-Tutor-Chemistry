"""Tests for safe database access."""

from pathlib import Path
from core.db import get_safe_db_connection

def test_get_safe_db_connection_new(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = get_safe_db_connection(db_path)
    assert conn is not None
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()

def test_get_safe_db_connection_corrupt(tmp_path: Path):
    db_path = tmp_path / "test_corrupt.db"
    # Write garbage to make it corrupt
    db_path.write_bytes(b"not a sqlite database")
    
    conn = get_safe_db_connection(db_path)
    assert conn is not None
    
    # Check that a backup was created
    backups = list(tmp_path.glob("test_corrupt.corrupt-*.db"))
    assert len(backups) == 1
    
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.close()
