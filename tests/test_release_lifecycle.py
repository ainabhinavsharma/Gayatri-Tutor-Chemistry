"""Tests for Windows Release Lifecycle: Installation, Upgrade, and Rollback (Acceptance Gate)."""

import sqlite3
import shutil
from pathlib import Path

from core.profile import ProfileManager, DEFAULT_PROFILE_ID
from core.session import SessionStore
from scripts.package_release import package_release


def test_fresh_installation_lifecycle(tmp_path: Path):
    """Acceptance Gate: Fresh installation initializes databases, tables, and default profiles cleanly."""
    fresh_db = tmp_path / "fresh_install" / "gayatri.db"
    assert not fresh_db.exists()

    # Cold start: SessionStore & ProfileManager create directory and schema
    store = SessionStore(db_path=fresh_db)
    pm = ProfileManager(db_path=fresh_db)

    assert fresh_db.exists()
    assert fresh_db.stat().st_size > 0

    # Verify default profile seeded
    active_profile = pm.get_active_profile()
    assert active_profile.id == DEFAULT_PROFILE_ID
    assert active_profile.role == "student"

    # Verify pragmas and WAL mode
    conn = store.conn
    journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    assert journal_mode.lower() == "wal"


def test_upgrade_migration_lifecycle(tmp_path: Path):
    """Acceptance Gate: Upgrading an existing database preserves user history and adds new schema columns."""
    legacy_db = tmp_path / "legacy_v1.db"

    # Create a legacy V1 database with pre-Phase-4 schema
    conn = sqlite3.connect(str(legacy_db))
    with conn:
        conn.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                message_count INT
            );
            """
        )
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at, message_count) "
            "VALUES ('legacy_sess_1', 'Old Session', '2026-01-01T00:00:00', '2026-01-01T00:00:00', 2);"
        )
    conn.close()

    # Run upgrade by initializing modern SessionStore & ProfileManager on it
    store = SessionStore(db_path=legacy_db)
    pm = ProfileManager(db_path=legacy_db)

    # Verify legacy session preserved with default profile assigned
    sessions = store.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["id"] == "legacy_sess_1"
    assert sessions[0]["profile_id"] == "default"

    # Verify user_profiles table was successfully added
    profiles = pm.list_profiles()
    assert len(profiles) >= 1


def test_rollback_resilience_lifecycle(tmp_path: Path):
    """Acceptance Gate: Failed database modifications can roll back safely from snapshot."""
    live_db = tmp_path / "live_production.db"
    backup_db = tmp_path / "live_production.db.bak"

    # Initialize live DB with valuable state
    pm = ProfileManager(db_path=live_db)
    p = pm.create_profile(username="student_critical", display_name="Critical Data")

    # Take pre-upgrade backup snapshot
    shutil.copy2(live_db, backup_db)
    assert backup_db.exists()

    # Simulate catastrophic upgrade / write failure by corrupting the live DB
    live_db.write_text("CORRUPTED_DURING_FAILED_UPGRADE_STEP", encoding="utf-8")

    # Rollback action: restore from backup snapshot
    shutil.copy2(backup_db, live_db)

    # Re-open database after rollback
    pm_restored = ProfileManager(db_path=live_db)
    restored_profile = pm_restored.get_profile(p.id)
    assert restored_profile is not None
    assert restored_profile.username == "student_critical"


def test_package_release_generates_verified_distribution(tmp_path: Path):
    """Acceptance Gate: Automated package release produces valid artifact and manifest."""
    release_dir = tmp_path / "dist_release"
    res = package_release(output_dir=release_dir)

    assert Path(res["manifest_path"]).exists()
    assert res["total_files"] > 10
    assert (release_dir / "app").exists()
    assert (release_dir / "core").exists()
    assert (release_dir / "requirements.lock").exists()
