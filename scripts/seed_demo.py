#!/usr/bin/env python3
"""Gayatri AI — Demo Seed Script (Section 50).

Seeds the demo student, knowledge base, learning dependency graph,
and baseline event logs for demo recordings.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from scripts.reset_demo import reset_demo
from scripts.ingest_knowledge import ingest_knowledge
from scripts.validate_learning_graph import validate_learning_graph


def seed_demo() -> bool:
    print("=" * 65)
    print("GAYATRI CHEMISTRY TUTOR — SEED DEMO ENVIRONMENT")
    print("=" * 65)

    print("\n1. Resetting demo student state...")
    reset_demo()

    print("\n2. Ingesting private knowledge base...")
    ingest_knowledge()

    print("\n3. Validating learning graph...")
    validate_learning_graph()

    print("\n" + "=" * 65)
    print("DEMO ENVIRONMENT SEEDING: COMPLETE & READY FOR RECORDING")
    print("=" * 65)
    return True


if __name__ == "__main__":
    seed_demo()
