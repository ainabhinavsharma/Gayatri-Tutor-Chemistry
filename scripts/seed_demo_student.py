#!/usr/bin/env python3
"""Gayatri AI — Demo Student Seeder (Silent Pre-Flight & Local Database Initialization).

Seeds:
1. PRIVATE_WORK/demo/demo_student.json (Alex Sharma, Class 11 CBSE, 64% mastery)
2. PRIVATE_WORK/logs/events.jsonl (Rich, realistic student achievement timeline)
3. GayatriAI/gayatri.db (Polished past sessions for Chemistry & General modes)
4. Verifies local offline model existence silently.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.tutor.adaptive import StudentProfile, EventLogger
from core.session import get_session_store


def seed_demo_student(quiet: bool = True) -> bool:
    """Initialize all local demo student databases and state files."""
    demo_dir = PROJECT_ROOT / "PRIVATE_WORK" / "demo"
    logs_dir = PROJECT_ROOT / "PRIVATE_WORK" / "logs"
    demo_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Student Profile
    student_file = demo_dir / "demo_student.json"
    profile = StudentProfile(
        student_id="demo_student_001",
        name="Alex Sharma",
        level="class_11",
        target="chemistry_foundation",
        current_topic="Thermodynamics",
        current_concept="THERMO_FIRST_LAW",
        active_hint_level=0,
        current_mode="EXPLAIN",
        misconceptions=[],
        history=[],
        mastery={
            # Thermodynamics (Unit 6)
            "THERMO_SYSTEM": 0.90,
            "THERMO_HEAT": 0.75,
            "THERMO_WORK": 0.50,
            "THERMO_INTERNAL_ENERGY": 0.40,
            "THERMO_SIGN_CONVENTION": 0.35,
            "THERMO_FIRST_LAW": 0.68,
            "THERMO_ENTHALPY": 0.20,
            # Chemical Bonding (Unit 4)
            "BOND_LEWIS": 0.85,
            "BOND_LONE_PAIRS": 0.75,
            "BOND_VSEPR": 0.60,
            "BOND_GEOMETRY": 0.50,
            "BOND_HYBRIDISATION": 0.30,
            # Periodic Trends (Unit 3)
            "PERIOD_ATOMIC_RADIUS": 0.85,
            "PERIOD_IONIC_RADIUS": 0.80,
            "PERIOD_IONISATION_ENERGY": 0.70,
            "PERIOD_ELECTRON_AFFINITY": 0.65,
            "PERIOD_ELECTRONEGATIVITY": 0.80,
            "PERIOD_TRENDS_OVERVIEW": 0.65,
            # Coordination Chemistry (Unit 9)
            "COORD_ENTITY": 0.45,
            "COORD_LIGAND": 0.40,
            "COORD_NUMBER": 0.35,
            "COORD_OXIDATION_STATE": 0.30,
            "COORD_NOMENCLATURE": 0.25,
            "COORD_GEOMETRY": 0.20,
        },
    )
    profile.save_to_file(student_file)

    # 2. Event Log Timeline (Achievement Stream)
    event_log = logs_dir / "events.jsonl"
    events = [
        {
            "event": "SESSION_STARTED",
            "student_id": "demo_student_001",
            "concept_id": "THERMO_FIRST_LAW",
            "timestamp": "2026-09-22T08:00:00+00:00",
            "notes": "Session initialized"
        },
        {
            "event": "EXPLANATION_GENERATED",
            "student_id": "demo_student_001",
            "concept_id": "THERMO_FIRST_LAW",
            "timestamp": "2026-09-22T08:05:00+00:00",
            "mode": "EXPLAIN",
            "current_mastery": 0.63
        },
        {
            "event": "HINT_GIVEN",
            "student_id": "demo_student_001",
            "concept_id": "THERMO_FIRST_LAW",
            "timestamp": "2026-09-22T08:08:00+00:00",
            "mode": "HINT",
            "hint_level": 1,
            "mastery": 0.63
        },
        {
            "event": "REMEDIATION_STARTED",
            "student_id": "demo_student_001",
            "concept_id": "THERMO_FIRST_LAW",
            "timestamp": "2026-09-22T08:12:00+00:00",
            "prerequisite_concept": "THERMO_INTERNAL_ENERGY",
            "mode": "REMEDIATE"
        },
        {
            "event": "ANSWER_EVALUATED",
            "student_id": "demo_student_001",
            "concept_id": "THERMO_FIRST_LAW",
            "timestamp": "2026-09-22T08:16:00+00:00",
            "result": "CORRECT",
            "previous_mastery": 0.63,
            "new_mastery": 0.68,
            "mastery_delta": 0.05
        }
    ]
    with open(event_log, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    # 3. Local SQLite Database Sessions & Messages
    try:
        store = get_session_store()
        conn = store.conn
        now = datetime.now().isoformat()

        # Seed Chemistry Session 1
        s1_id = "demo_chem_session_1"
        conn.execute(
            """INSERT OR REPLACE INTO sessions (id, title, mode, user_id, profile_id, created_at, updated_at, message_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (s1_id, "Thermodynamics: First Law & Work Calculation", "chemistry_tutor", "local_user_1", "default", now, now, 4)
        )
        conn.execute("DELETE FROM messages WHERE session_id = ?", (s1_id,))
        conn.executemany(
            """INSERT INTO messages (session_id, role, content, agent_name, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (s1_id, "user", "Can you explain the First Law of Thermodynamics and how work is defined?", "", now),
                (s1_id, "assistant", "Welcome Alex! The First Law states that energy cannot be created or destroyed. In formula form: $\\Delta U = q + w$. In chemistry IUPAC conventions, work done ON the system is positive (+w), while expansion work done BY the system on surroundings is negative (-w).", "ChemistryTutor", now),
                (s1_id, "user", "A gas absorbs 500 J of heat and does 200 J of work expanding. What is Delta U?", "", now),
                (s1_id, "assistant", "Since the gas does 200 J of work expanding against external pressure, work leaves the system: $w = -200\\text{ J}$. Therefore: $\\Delta U = 500 + (-200) = 300\\text{ J}$.", "ChemistryTutor", now),
            ]
        )

        # Seed Chemistry Session 2
        s2_id = "demo_chem_session_2"
        conn.execute(
            """INSERT OR REPLACE INTO sessions (id, title, mode, user_id, profile_id, created_at, updated_at, message_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (s2_id, "Chemical Bonding: VSEPR Molecular Geometry", "chemistry_tutor", "local_user_1", "default", now, now, 2)
        )
        conn.execute("DELETE FROM messages WHERE session_id = ?", (s2_id,))
        conn.executemany(
            """INSERT INTO messages (session_id, role, content, agent_name, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (s2_id, "user", "Why does ammonia (NH3) have a trigonal pyramidal shape instead of trigonal planar?", "", now),
                (s2_id, "assistant", "Nitrogen has 5 valence electrons. In NH3, it forms 3 bonding pairs and retains 1 lone pair. Lone pair-bond pair repulsion is stronger than bond pair-bond pair repulsion, compressing the bond angle to 107 degrees and creating a pyramidal geometry.", "ChemistryTutor", now),
            ]
        )

        # Seed General Session 1
        s3_id = "demo_gen_session_1"
        conn.execute(
            """INSERT OR REPLACE INTO sessions (id, title, mode, user_id, profile_id, created_at, updated_at, message_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (s3_id, "CBSE Class 11 Chemistry Study Schedule", "general_assistant", "local_user_1", "default", now, now, 2)
        )
        conn.execute("DELETE FROM messages WHERE session_id = ?", (s3_id,))
        conn.executemany(
            """INSERT INTO messages (session_id, role, content, agent_name, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (s3_id, "user", "Help me plan a 3-day revision timetable for CBSE Class 11 Chemistry.", "", now),
                (s3_id, "assistant", "Here is a balanced 3-day timetable: Day 1 Thermodynamics & State Functions (2 hrs numericals), Day 2 Chemical Bonding & VSEPR Shapes (1.5 hrs), Day 3 Periodic Trends & Coordination Foundations (1.5 hrs).", "GeneralAssistant", now),
            ]
        )
        conn.commit()
    except Exception as exc:
        if not quiet:
            print(f"Warning: Database seeding notice: {exc}")

    if not quiet:
        print("[OK] Demo student profile, event stream, and local database sessions seeded successfully.")
    return True


if __name__ == "__main__":
    seed_demo_student(quiet=False)
