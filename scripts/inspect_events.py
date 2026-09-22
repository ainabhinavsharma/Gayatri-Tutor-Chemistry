#!/usr/bin/env python3
"""Gayatri AI — Event Inspection Script (Section 53).

Usage:
    python scripts/inspect_events.py [student_id] [--concept CID] [--type TYPE] [--last N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.tutor.adaptive import EventLogger


def inspect_events(
    student_id: str = "demo_student_001",
    concept_filter: str | None = None,
    type_filter: str | None = None,
    limit: int = 20,
) -> None:
    print("=" * 75)
    print(f"EVENT TIMELINE LOG INSPECTION: {student_id}")
    print("=" * 75)

    logger = EventLogger()
    events = logger.get_recent_events(student_id=student_id, limit=200)

    if concept_filter:
        events = [e for e in events if concept_filter.lower() in e.get("concept_id", "").lower()]
    if type_filter:
        events = [e for e in events if type_filter.lower() in e.get("event", "").lower()]

    events = events[-limit:]

    if not events:
        print("No matching events found in event log.")
        print("=" * 75)
        return

    print(f"Showing last {len(events)} events (most recent last):\n")
    for e in events:
        ts = e.get("timestamp", "")
        time_part = ts.split("T")[-1][:8] if "T" in ts else ts[:8]
        ename = e.get("event", "")
        cid = e.get("concept_id", "")
        extra = []
        if "result" in e:
            extra.append(f"res={e['result']}")
        if "mastery_delta" in e:
            extra.append(f"delta={e['mastery_delta']:+.2f}")
        if "new_mastery" in e:
            extra.append(f"new={e['new_mastery']:.0%}")
        if "hint_level" in e:
            extra.append(f"hint_lvl={e['hint_level']}")
        if "misconception" in e and e["misconception"]:
            extra.append(f"misc={e['misconception']}")
        if "prerequisite_concept" in e:
            extra.append(f"prereq={e['prerequisite_concept']}")

        extra_str = f" | ({', '.join(extra)})" if extra else ""
        print(f"  {time_part}  {ename:25s}  {cid:22s}{extra_str}")

    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect recent tutor events")
    parser.add_argument("student_id", nargs="?", default="demo_student_001")
    parser.add_argument("--concept", default=None, help="Filter by concept ID")
    parser.add_argument("--type", default=None, help="Filter by event type")
    parser.add_argument("--last", type=int, default=20, help="Number of events to display")
    args = parser.parse_args()

    inspect_events(
        student_id=args.student_id,
        concept_filter=args.concept,
        type_filter=args.type,
        limit=args.last,
    )
