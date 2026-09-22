"""Tests for Student Progress & Mastery Dashboard (Phase 9 & Demo Integration).

Verifies:
1. build_student_dashboard_payload schema and statistical accuracy
2. Chapter progress aggregation across the 4 senior secondary units
3. Prerequisite Roadmap DAG node classification (mastered, focus, practicing, locked)
4. Pedagogical translation of misconceptions into constructive study guidance
5. Humanization of event telemetry into an achievement timeline
6. Bridge slots (get_student_dashboard, launch_concept_session) serialization and state updates
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.learning.progress import build_student_dashboard_payload
from core.tutor.adaptive import EventLogger, StudentProfile
from app.bridge.facade import Bridge


@pytest.fixture
def clean_student_and_events(tmp_path, monkeypatch):
    """Set up isolated student and event log paths for testing."""
    student_file = tmp_path / "test_student.json"
    event_log = tmp_path / "test_events.jsonl"

    profile = StudentProfile(
        student_id="test_student_001",
        name="Alex Sharma",
        level="class_11",
        target="chemistry_foundation",
        current_topic="Thermodynamics",
        current_concept="THERMO_FIRST_LAW",
        active_hint_level=1,
        current_mode="EXPLAIN",
        misconceptions=["THERMO_SIGN_CONVENTION"],
        mastery={
            "THERMO_SYSTEM": 0.90,
            "THERMO_HEAT": 0.75,
            "THERMO_WORK": 0.50,
            "THERMO_INTERNAL_ENERGY": 0.40,
            "THERMO_SIGN_CONVENTION": 0.35,
            "THERMO_FIRST_LAW": 0.68,
            "THERMO_ENTHALPY": 0.20,
            "BOND_LEWIS": 0.85,
            "BOND_LONE_PAIRS": 0.75,
            "BOND_VSEPR": 0.60,
            "BOND_GEOMETRY": 0.50,
            "BOND_HYBRIDISATION": 0.30,
            "PERIOD_ATOMIC_RADIUS": 0.85,
            "PERIOD_IONIC_RADIUS": 0.80,
            "PERIOD_IONISATION_ENERGY": 0.70,
            "PERIOD_ELECTRON_AFFINITY": 0.65,
            "PERIOD_ELECTRONEGATIVITY": 0.80,
            "PERIOD_TRENDS_OVERVIEW": 0.65,
            "COORD_ENTITY": 0.45,
            "COORD_LIGAND": 0.40,
            "COORD_NUMBER": 0.35,
            "COORD_OXIDATION_STATE": 0.30,
            "COORD_NOMENCLATURE": 0.25,
            "COORD_GEOMETRY": 0.20,
        },
    )
    profile.save_to_file(student_file)

    logger = EventLogger(log_path=event_log)
    logger.log_event("SESSION_STARTED", "test_student_001", "THERMO_FIRST_LAW")
    logger.log_event("EXPLANATION_GENERATED", "test_student_001", "THERMO_FIRST_LAW")
    logger.log_event("HINT_GIVEN", "test_student_001", "THERMO_FIRST_LAW", {"hint_level": 2})
    logger.log_event("REMEDIATION_STARTED", "test_student_001", "THERMO_FIRST_LAW", {"prerequisite_concept": "THERMO_INTERNAL_ENERGY"})
    logger.log_event("ANSWER_EVALUATED", "test_student_001", "THERMO_FIRST_LAW", {
        "result": "CORRECT",
        "previous_mastery": 0.63,
        "new_mastery": 0.68,
        "mastery_delta": 0.05,
    })

    # Monkeypatch default paths in adaptive module
    import core.tutor.adaptive as adaptive_mod
    monkeypatch.setattr(adaptive_mod, "DEFAULT_STUDENT_FILE", student_file)
    monkeypatch.setattr(adaptive_mod, "DEFAULT_EVENT_LOG", event_log)

    return profile, logger


def test_build_student_dashboard_payload_structure(clean_student_and_events):
    """Verify that build_student_dashboard_payload generates all required dashboard keys."""
    data = build_student_dashboard_payload()

    assert data["ok"] is True
    assert "student" in data
    assert "chapters" in data
    assert "roadmap" in data
    assert "focus_area" in data
    assert "spaced_review" in data
    assert "activity_stream" in data

    # Check student identity
    st = data["student"]
    assert st["name"] == "Alex Sharma"
    assert st["initials"] == "AS"
    assert st["level"] == "Class 11 CBSE Chemistry"
    assert st["streak_days"] >= 1
    assert st["mastered_count"] >= 1
    assert st["total_concepts"] == 24


def test_chapters_matrix(clean_student_and_events):
    """Verify that all 4 NCERT chapters are present with valid scores and action prompts."""
    data = build_student_dashboard_payload()
    chapters = data["chapters"]

    assert len(chapters) == 4
    chapter_ids = [ch["id"] for ch in chapters]
    assert "thermodynamics" in chapter_ids
    assert "bonding" in chapter_ids
    assert "periodicity" in chapter_ids
    assert "coordination" in chapter_ids

    for ch in chapters:
        assert 0 <= ch["mastery_pct"] <= 100
        assert ch["color"].startswith("#")
        assert len(ch["action_text"]) > 0
        assert len(ch["target_concept"]) > 0
        assert len(ch["prompt"]) > 0


def test_roadmap_dag_classification(clean_student_and_events):
    """Verify that prerequisite nodes for active chapter have correct statuses."""
    data = build_student_dashboard_payload()
    roadmap = data["roadmap"]

    assert roadmap["topic_title"] == "Thermodynamics"
    nodes = roadmap["nodes"]
    assert len(nodes) == 5

    node_map = {n["id"]: n for n in nodes}
    # Current active concept in fixture is THERMO_FIRST_LAW
    assert node_map["THERMO_FIRST_LAW"]["status"] == "focus"
    assert "Focus" in node_map["THERMO_FIRST_LAW"]["status_text"]

    # High mastery concept (0.90) should be mastered
    assert node_map["THERMO_SYSTEM"]["status"] == "mastered"
    assert "Mastered" in node_map["THERMO_SYSTEM"]["status_text"]

    # Low mastery concept (0.20) should be locked or exploring
    assert node_map["THERMO_ENTHALPY"]["status"] == "locked"


def test_focus_area_misconception_translation(clean_student_and_events):
    """Verify that THERMO_SIGN_CONVENTION is translated into non-punitive guidance."""
    data = build_student_dashboard_payload()
    fa = data["focus_area"]

    assert fa["topic"] == "Chemical Thermodynamics"
    assert "w < 0" in fa["tip"] or "work is negative" in fa["tip"].lower()
    assert len(fa["prompt"]) > 0


def test_activity_stream_humanization(clean_student_and_events):
    """Verify that raw events are translated into positive student achievements."""
    data = build_student_dashboard_payload()
    stream = data["activity_stream"]

    assert len(stream) >= 3

    titles = [item["title"] for item in stream]
    # Check that humanized titles exist
    assert any("Correct Answer" in t for t in titles)
    assert any("Unlocked Hint" in t for t in titles)
    assert any("Reinforced Prerequisite" in t for t in titles)

    # Check that mastery boost badge was captured for the correct answer
    correct_item = next(item for item in stream if "Correct Answer" in item["title"])
    assert correct_item["badge"] is not None
    assert "+5% Mastery Boost" in correct_item["badge"]


def test_bridge_get_student_dashboard(clean_student_and_events):
    """Verify that Bridge.get_student_dashboard returns valid JSON string."""
    bridge = Bridge()
    raw = bridge.get_student_dashboard()
    parsed = json.loads(raw)

    assert parsed["ok"] is True
    assert parsed["student"]["name"] == "Alex Sharma"


def test_bridge_launch_concept_session(clean_student_and_events):
    """Verify that Bridge.launch_concept_session updates student's active concept and topic."""
    bridge = Bridge()
    bridge.launch_concept_session("BOND_GEOMETRY", "Why is ammonia pyramidal?")

    st = StudentProfile.load_from_file()
    assert st.current_concept == "BOND_GEOMETRY"
    assert st.current_topic == "Chemical Bonding"


def test_bridge_get_session_messages():
    """Verify that Bridge and ChatBridge get_session_messages slots return valid session messages."""
    from app.bridge.chat import ChatBridge
    from core.session import get_session_store

    store = get_session_store()
    conn = store.conn
    s_id = "test_restore_session_1"
    from datetime import datetime
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, title, mode, user_id, message_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (s_id, "Test Restore", "chemistry_tutor", "local_user_1", 2, now, now)
    )
    conn.execute("DELETE FROM messages WHERE session_id = ?", (s_id,))
    conn.execute(
        "INSERT INTO messages (session_id, role, content, agent_name, timestamp) VALUES (?, ?, ?, ?, ?)",
        (s_id, "user", "Hello tutor!", "", now)
    )
    conn.execute(
        "INSERT INTO messages (session_id, role, content, agent_name, timestamp) VALUES (?, ?, ?, ?, ?)",
        (s_id, "assistant", "Hello student! What would you like to learn?", "ChemistryTutor", now)
    )
    conn.commit()

    bridge = Bridge()
    chat_bridge = ChatBridge(bridge)

    raw = bridge.get_session_messages(s_id)
    data = json.loads(raw)
    assert data["ok"] is True
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello tutor!"
    assert data["messages"][1]["role"] == "assistant"

    raw_chat = chat_bridge.get_session_messages(s_id)
    data_chat = json.loads(raw_chat)
    assert data_chat["ok"] is True
    assert len(data_chat["messages"]) == 2
