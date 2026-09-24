"""Gayatri AI — Post-build release strip script.

Run after pyinstaller to remove debug/dev-only files from dist/.
Saves ~85-100 MB and prevents Windows Defender false-positives on .debug.pak files.

Usage:
    python scripts/strip_release_build.py
"""
from __future__ import annotations

import shutil
from pathlib import Path

DIST_DIR = Path(__file__).parent.parent / "dist" / "Gayatri_Chemistry_Tutor"
INTERNAL_DIR = DIST_DIR / "_internal"
PYSIDE6_DIR = INTERNAL_DIR / "PySide6"
RESOURCES_DIR = PYSIDE6_DIR / "resources"


def strip_debug_pak_files():
    """Remove Qt WebEngine debug resource files (dev-only, not needed in release)."""
    patterns = [
        "*.debug.pak",
        "*.debug.bin",
        "v8_context_snapshot.debug.bin",
    ]
    removed = []
    if RESOURCES_DIR.exists():
        for pattern in patterns:
            for f in RESOURCES_DIR.glob(pattern):
                size_mb = round(f.stat().st_size / 1024 / 1024, 1)
                f.unlink()
                removed.append((f.name, size_mb))
                print(f"  [STRIPPED] {f.name} ({size_mb} MB)")
    return removed


def strip_unused_qt_dlls():
    """Remove Qt6 DLLs that are not needed for this app (saves ~15-25 MB)."""
    # These modules are pulled in by PyInstaller but not used by the app
    unused_dlls = [
        "opengl32sw.dll",          # 19.7 MB — software OpenGL renderer (not needed with WebEngine)
    ]
    removed = []
    for dll_name in unused_dlls:
        # Check both PySide6/ dir and _internal/ dir
        for search_dir in [PYSIDE6_DIR, INTERNAL_DIR]:
            dll_path = search_dir / dll_name
            if dll_path.exists():
                size_mb = round(dll_path.stat().st_size / 1024 / 1024, 1)
                dll_path.unlink()
                removed.append((dll_name, size_mb))
                print(f"  [STRIPPED] {dll_name} ({size_mb} MB) from {search_dir.name}/")
    return removed


def strip_private_work():
    """Remove PRIVATE_WORK directory if it was accidentally included."""
    private_dir = INTERNAL_DIR / "PRIVATE_WORK"
    if private_dir.exists():
        shutil.rmtree(private_dir)
        print("  [STRIPPED] PRIVATE_WORK/ directory (private IP — should not ship)")
        return True
    return False


def strip_training_data():
    """Remove any *.jsonl or *.csv files accidentally bundled."""
    removed = []
    for ext in ["*.jsonl", "*.csv", "*.safetensors"]:
        for f in DIST_DIR.rglob(ext):
            size_mb = round(f.stat().st_size / 1024 / 1024, 1)
            f.unlink()
            removed.append((f.name, size_mb))
            print(f"  [STRIPPED] {f.name} ({size_mb} MB)")
    return removed


def print_final_size():
    total = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())
    print(f"\n  [SIZE] Final dist size: {total / 1024 / 1024:.1f} MB")


def main():
    print("=" * 60)
    print("  Gayatri AI — Release Strip Script")
    print("=" * 60)

    if not DIST_DIR.exists():
        print(f"[ERROR] dist dir not found: {DIST_DIR}")
        print("  Run pyinstaller first: python -m PyInstaller packaging/gayatri_demo.spec")
        raise SystemExit(1)

    print(f"\n[1] Stripping debug PAK files from {RESOURCES_DIR.name if RESOURCES_DIR.exists() else 'resources'}...")
    pak_removed = strip_debug_pak_files()

    print("\n[2] Stripping unused Qt DLLs...")
    dll_removed = strip_unused_qt_dlls()

    print("\n[3] Checking for PRIVATE_WORK...")
    strip_private_work()

    print("\n[4] Checking for accidentally bundled data files...")
    data_removed = strip_training_data()

    total_stripped = sum(mb for _, mb in pak_removed + dll_removed + data_removed)
    print(f"\n  [SUMMARY] Stripped {len(pak_removed + dll_removed + data_removed)} files, saved {total_stripped:.1f} MB")
    print_final_size()
    print("\n  [DONE] Strip complete. Ready to package.")


if __name__ == "__main__":
    main()
