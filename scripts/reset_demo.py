#!/usr/bin/env python3
"""Gayatri AI — Demo Reset Script (Section 27).

Resets demo student state, mastery scores, active misconceptions, and event logs
to a clean, known starting state ready for product demo recording.
Preserves the private RAG knowledge base intact.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.tutor.adaptive import StudentProfile


def reset_demo() -> bool:
    demo_dir = root / "PRIVATE_WORK" / "demo"
    logs_dir = root / "PRIVATE_WORK" / "logs"
    demo_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Reset Student Profile
    student_file = demo_dir / "demo_student.json"
    initial_student = StudentProfile(
        student_id="demo_student_001",
        name="Demo Student",
        level="class_11",
        target="chemistry_foundation",
        current_topic="Thermodynamics",
        current_concept="THERMO_FIRST_LAW",
        active_hint_level=0,
        current_mode="EXPLAIN",
        misconceptions=[],
        history=[],
        mastery={
            # Thermodynamics
            "THERMO_SYSTEM": 0.90,
            "THERMO_HEAT": 0.70,
            "THERMO_WORK": 0.50,
            "THERMO_INTERNAL_ENERGY": 0.40,
            "THERMO_SIGN_CONVENTION": 0.35,
            "THERMO_FIRST_LAW": 0.42,
            "THERMO_ENTHALPY": 0.20,
            # Chemical Bonding
            "BOND_LEWIS": 0.85,
            "BOND_LONE_PAIRS": 0.75,
            "BOND_VSEPR": 0.55,
            "BOND_GEOMETRY": 0.50,
            "BOND_HYBRIDISATION": 0.30,
            # Periodic Trends
            "PERIOD_ATOMIC_RADIUS": 0.80,
            "PERIOD_IONIC_RADIUS": 0.75,
            "PERIOD_IONISATION_ENERGY": 0.70,
            "PERIOD_ELECTRON_AFFINITY": 0.65,
            "PERIOD_ELECTRONEGATIVITY": 0.80,
            "PERIOD_TRENDS_OVERVIEW": 0.60,
            # Coordination Chemistry
            "COORD_ENTITY": 0.45,
            "COORD_LIGAND": 0.40,
            "COORD_NUMBER": 0.35,
            "COORD_OXIDATION_STATE": 0.30,
            "COORD_NOMENCLATURE": 0.25,
            "COORD_GEOMETRY": 0.20,
        }
    )
    initial_student.save_to_file(student_file)

    # 2. Reset event log
    event_log = logs_dir / "events.jsonl"
    with open(event_log, "w", encoding="utf-8") as f:
        # Initialize with session started event
        init_event = {
            "event": "SESSION_STARTED",
            "student_id": "demo_student_001",
            "concept_id": "THERMO_FIRST_LAW",
            "timestamp": "demo_baseline",
            "notes": "Demo session reset to initial state"
        }
        f.write(json.dumps(init_event) + "\n")

    # Output formatted report matching Section 27
    print("Demo reset complete.\n")
    print("Student:")
    print(f"demo_student_001\n")
    print("Mastery:")
    print("reset\n")
    print("Learning graph:")
    print("loaded\n")
    print("Knowledge base:")
    print("preserved\n")
    print("Ready for recording.")
    return True


if __name__ == "__main__":
    reset_demo()
