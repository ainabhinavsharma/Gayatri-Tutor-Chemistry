"""Tests for Multi-User Profile Architecture (Phase 4)."""

from pathlib import Path
from core.profile import ProfileManager, DEFAULT_PROFILE_ID
from core.session import SessionStore


def test_profile_manager_initialization(tmp_path: Path):
    """Verify default profile is seeded automatically."""
    db_path = tmp_path / "profile_test.db"
    pm = ProfileManager(db_path)

    profiles = pm.list_profiles()
    assert len(profiles) >= 1
    default = pm.get_active_profile()
    assert default.id == DEFAULT_PROFILE_ID
    assert default.role == "student"


def test_profile_creation_and_switching(tmp_path: Path):
    """Verify creating learner and teacher profiles and switching between them."""
    db_path = tmp_path / "profile_test.db"
    pm = ProfileManager(db_path)

    # Create new student profile
    student = pm.create_profile(
        username="aarav",
        display_name="Aarav Sharma",
        grade="Grade 10",
        board="CBSE",
        role="student",
    )
    assert student.username == "aarav"
    assert student.grade == "Grade 10"

    # Create teacher profile
    teacher = pm.create_profile(
        username="priya_teacher",
        display_name="Priya Patel",
        role="teacher",
    )
    assert teacher.role == "teacher"

    # List profiles
    all_profiles = pm.list_profiles()
    usernames = [p.username for p in all_profiles]
    assert "aarav" in usernames
    assert "priya_teacher" in usernames

    # Switch active profile
    pm.switch_profile(student.id)
    assert pm.get_active_profile().id == student.id

    pm.switch_profile(teacher.id)
    assert pm.get_active_profile().id == teacher.id


def test_profile_session_filtering(tmp_path: Path):
    """Verify sessions can be queried per profile."""
    db_path = tmp_path / "profile_session_test.db"
    pm = ProfileManager(db_path)
    store = SessionStore(db_path)

    p1 = pm.create_profile(username="student1", display_name="Student One")
    p2 = pm.create_profile(username="student2", display_name="Student Two")

    # Insert sessions directly associated with profiles
    conn = store.conn
    with conn:
        conn.execute(
            "INSERT INTO sessions (id, profile_id, title, created_at, updated_at, message_count) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            ("sess_p1", p1.id, "Math Linear Equations", "2026-09-16T00:00:00", "2026-09-16T00:00:00", 3),
        )
        conn.execute(
            "INSERT INTO sessions (id, profile_id, title, created_at, updated_at, message_count) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            ("sess_p2", p2.id, "Science Optics", "2026-09-16T00:00:00", "2026-09-16T00:00:00", 5),
        )

    # Query filtered by profile
    p1_sessions = store.list_sessions(profile_id=p1.id)
    assert len(p1_sessions) == 1
    assert p1_sessions[0]["id"] == "sess_p1"

    p2_sessions = store.list_sessions(profile_id=p2.id)
    assert len(p2_sessions) == 1
    assert p2_sessions[0]["id"] == "sess_p2"

    # Query all
    all_sessions = store.list_sessions()
    assert len(all_sessions) == 2
