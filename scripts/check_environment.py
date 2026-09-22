#!/usr/bin/env python3
"""Gayatri AI — Environment verification script.

Verifies runtime environment, dependencies, directories, and database paths.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def check_environment() -> bool:
    print("=" * 60)
    print("GAYATRI CHEMISTRY TUTOR — ENVIRONMENT CHECK")
    print("=" * 60)

    all_passed = True

    # 1. Python version check
    py_ver = sys.version_info
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    py_ok = (py_ver.major == 3 and py_ver.minor >= 10)
    print(f"Python Version:       {py_str} ({'PASS' if py_ok else 'FAIL: requires >= 3.10'})")
    if not py_ok:
        all_passed = False

    # 2. OS & Architecture
    print(f"Operating System:     {platform.system()} {platform.release()} ({platform.machine()})")

    # 3. Virtual Environment
    in_venv = sys.prefix != sys.base_prefix
    print(f"Virtual Environment:  {sys.prefix} ({'PASS' if in_venv else 'WARNING: running outside venv'})")

    # 4. Dependency checks
    deps = [
        ("sqlite3", "Standard SQLite library"),
        ("pydantic", "Pydantic data validation"),
        ("pytest", "Pytest test framework"),
        ("PySide6", "PySide6 Qt GUI framework"),
        ("llama_cpp", "Llama-cpp local inference"),
    ]

    print("\nDependency Checks:")
    for mod_name, label in deps:
        try:
            __import__(mod_name)
            print(f"  - {mod_name:15s}: PASS ({label})")
        except ImportError as exc:
            print(f"  - {mod_name:15s}: FAIL ({exc})")
            all_passed = False

    # 5. Core directory verification
    print("\nDirectory Structure:")
    root = Path(__file__).resolve().parent.parent
    required_dirs = [
        root / "core",
        root / "app",
        root / "PRIVATE_WORK",
        root / "PRIVATE_WORK" / "knowledge",
        root / "PRIVATE_WORK" / "learning_graph",
        root / "PRIVATE_WORK" / "demo",
        root / "PRIVATE_WORK" / "logs",
        root / "PRIVATE_WORK" / "training",
    ]
    for d in required_dirs:
        rel = d.relative_to(root)
        exists = d.exists()
        print(f"  - {str(rel):30s}: {'EXISTS' if exists else 'MISSING'}")
        if not exists:
            d.mkdir(parents=True, exist_ok=True)
            print(f"    -> Created {rel}")

    # 6. Overall status
    print("\n" + "=" * 60)
    status_str = "PASS — Environment is fully configured" if all_passed else "FAIL — Some checks did not pass"
    print(f"OVERALL STATUS: {status_str}")
    print("=" * 60)
    return all_passed


if __name__ == "__main__":
    success = check_environment()
    sys.exit(0 if success else 1)
