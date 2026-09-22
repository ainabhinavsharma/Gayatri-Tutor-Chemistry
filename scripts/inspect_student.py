#!/usr/bin/env python3
"""Gayatri AI — Student Inspection Script (Section 51).

Usage:
    python scripts/inspect_student.py [student_id]
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.tutor.adaptive import EventLogger, StudentProfile


def inspect_student(student_id: str = "demo_student_001") -> None:
    print("=" * 65)
    print(f"STUDENT PROFILE INSPECTION: {student_id}")
    print("=" * 65)

    student = StudentProfile.load_from_file()
    logger = EventLogger()
    events = logger.get_recent_events(student_id=student_id, limit=20)

    print(f"Student ID:           {student.student_id}")
    print(f"Name:                 {student.name}")
    print(f"Academic Level:       {student.level}")
    print(f"Learning Target:      {student.target}")
    print(f"Current Topic:        {student.current_topic}")
    print(f"Current Concept:      {student.current_concept}")
    print(f"Active Mode:          {student.current_mode}")

    curr_mastery = student.get_mastery(student.current_concept)
    print(f"Current Mastery:      {curr_mastery:.0%}")

    # Find weak concepts (< 50%)
    weak = [cid for cid, m in student.mastery.items() if m < 0.50]
    print("\nWeak Concepts (< 50%):")
    if weak:
        for w in weak[:6]:
            print(f"  - {w:25s}: {student.mastery[w]:.0%}")
    else:
        print("  - None (all concepts >= 50%)")

    # Recommended next action
    print("\nActive Misconceptions:")
    if student.misconceptions:
        for m in student.misconceptions:
            print(f"  - {m}")
    else:
        print("  - None recorded")

    print(f"\nRecent Events Logged ({len(events)} events):")
    for evt in events[-5:]:
        t = evt.get("timestamp", "").split("T")[-1][:8]
        ename = evt.get("event", "")
        cid = evt.get("concept_id", "")
        print(f"  [{t}] {ename:25s} | {cid}")

    print("=" * 65)


if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "demo_student_001"
    inspect_student(sid)
