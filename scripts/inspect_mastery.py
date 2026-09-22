#!/usr/bin/env python3
"""Gayatri AI — Mastery Inspection Script (Section 52).

Usage:
    python scripts/inspect_mastery.py [student_id]
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


def inspect_mastery(student_id: str = "demo_student_001") -> None:
    print("=" * 70)
    print(f"MASTERY MODEL INSPECTION: {student_id}")
    print("=" * 70)

    student = StudentProfile.load_from_file()

    # Load prerequisites to determine blocked concepts
    p_path = root / "PRIVATE_WORK" / "learning_graph" / "prerequisites.json"
    prereqs = {}
    if p_path.exists():
        with open(p_path, encoding="utf-8") as f:
            for item in json.load(f).get("dependencies", []):
                prereqs[item["concept_id"]] = item.get("prerequisites", [])

    items = sorted(student.mastery.items(), key=lambda x: x[1])

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        bar_char = "█"
        empty_char = "░"
    except Exception:
        bar_char = "#"
        empty_char = "-"

    print("Concept Mastery Gauge:")
    for cid, m in items:
        bars = int(m * 20)
        try:
            gauge = bar_char * bars + empty_char * (20 - bars)
            print(f"  {cid:25s} [{gauge}] {m:4.0%}")
        except UnicodeEncodeError:
            gauge = "#" * bars + "-" * (20 - bars)
            print(f"  {cid:25s} [{gauge}] {m:4.0%}")

    lowest = items[0] if items else ("None", 0.0)
    highest = items[-1] if items else ("None", 0.0)

    # Mastered (>= 80%)
    mastered = [cid for cid, m in items if m >= 0.80]

    # Blocked concepts (prerequisite < 50%)
    blocked = []
    for cid, plist in prereqs.items():
        if student.get_mastery(cid) < 0.80:
            for p in plist:
                if student.get_mastery(p) < 0.50:
                    blocked.append((cid, p, student.get_mastery(p)))
                    break

    print("\nAnalytics & Prerequisite Routing:")
    print(f"  Lowest Mastery:      {lowest[0]} ({lowest[1]:.0%})")
    print(f"  Highest Mastery:     {highest[0]} ({highest[1]:.0%})")
    print(f"  Mastered Concepts:   {len(mastered)} ({', '.join(mastered[:4])}...)")

    print("\nConcepts Blocked by Prerequisite Deficit:")
    if blocked:
        for cid, p, pscore in blocked:
            print(f"  - {cid:22s} -> Blocked by '{p}' ({pscore:.0%})")
    else:
        print("  - None (all prerequisites meet foundation threshold)")

    # Recommended next concept
    unmastered = [cid for cid, m in items if m < 0.80 and cid not in [b[0] for b in blocked]]
    rec = unmastered[0] if unmastered else "All concepts mastered"
    print(f"\nRecommended Next Concept: {rec}")
    print("=" * 70)


if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "demo_student_001"
    inspect_mastery(sid)
