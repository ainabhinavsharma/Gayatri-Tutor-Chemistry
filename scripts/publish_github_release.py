#!/usr/bin/env python3
"""Gayatri AI — Publish release assets to GitHub repository.

Target: https://github.com/Gayatri-Education/Gayatri-Tutor-ChemistryDemo
Tags the repository, pushes to remote, and creates a GitHub Release with assets.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RELEASE_STAGING = PROJECT_ROOT / "release_staging"
TARGET_REPO = "https://github.com/Gayatri-Education/Gayatri-Tutor-ChemistryDemo.git"


def run_git(args: list[str]) -> str:
    """Run a git command and return its output."""
    cmd = ["git"] + args
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def setup_git_remote():
    """Ensure git remote 'demo' points to the target repository."""
    remotes = run_git(["remote", "-v"])
    if "demo" in remotes:
        run_git(["remote", "set-url", "demo", TARGET_REPO])
        print(f"[OK] Updated remote 'demo' -> {TARGET_REPO}")
    else:
        run_git(["remote", "add", "demo", TARGET_REPO])
        print(f"[OK] Added remote 'demo' -> {TARGET_REPO}")


def prepare_tag(version: str = "v3.0.0"):
    """Tag commit with release version."""
    tags = run_git(["tag", "-l"])
    if version in tags.split():
        print(f"[*] Tag {version} already exists locally.")
    else:
        run_git(["tag", "-a", version, "-m", f"Gayatri Chemistry Tutor {version} Demo Release"])
        print(f"[OK] Created git tag {version}")


def main():
    print("============================================================")
    print("  GAYATRI CHEMISTRY TUTOR — GitHub Release Publisher")
    print(f"  Target: {TARGET_REPO}")
    print("============================================================\n")

    setup_git_remote()
    prepare_tag("v3.0.0")

    print("\nAssets ready in release_staging/:")
    for f in sorted(RELEASE_STAGING.glob("*")):
        if f.is_file():
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  - {f.name} ({size_mb:.1f} MB)")

    print("\nNext steps to publish to GitHub:")
    print("1. Push commit and tag:")
    print("   git push demo main --tags")
    print("2. Create release via GitHub CLI or Web:")
    print("   Open https://github.com/Gayatri-Education/Gayatri-Tutor-ChemistryDemo/releases/new")
    print("   Tag: v3.0.0")
    print("   Title: Gayatri Chemistry Tutor v3.0.0 (Local Offline Demo Release)")
    print("   Upload all files from 'release_staging/' folder!")


if __name__ == "__main__":
    main()
