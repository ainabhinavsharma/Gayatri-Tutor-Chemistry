#!/usr/bin/env python3
"""Gayatri AI — Master Automated Packaging & GitHub Release Generator.

1. Freezes application into standalone binary using PyInstaller.
2. Embeds clean-slate database schema (zero dummy chats).
3. Bundles 3B model (Gayatri-Tutor-v3-Q4_K_M.gguf) and NCERT RAG chunks.
4. Packages 1-Click Portable ZIP (release_staging/Gayatri_Chemistry_Tutor_Portable_v3.0.0.zip).
5. Compiles Inno Setup installer if ISCC.exe is available.
6. Computes SHA-256 hashes into release_staging/SHA256SUMS.txt.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
DIST_DIR = PROJECT_ROOT / "dist" / "Gayatri_Chemistry_Tutor"
RELEASE_STAGING = PROJECT_ROOT / "release_staging"


def compute_sha256(filepath: Path) -> str:
    """Compute cryptographic SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def ensure_pyinstaller() -> None:
    """Verify PyInstaller is installed in the active environment."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller found ({PyInstaller.__version__})")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_pyinstaller() -> None:
    """Run PyInstaller with packaging/gayatri_demo.spec."""
    print("=" * 60)
    print("  [1/5] Compiling Standalone Binary via PyInstaller...")
    print("=" * 60)
    spec_path = PROJECT_ROOT / "packaging" / "gayatri_demo.spec"
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found at {spec_path}")

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec_path)]
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)

    exe_path = DIST_DIR / "Gayatri_Chemistry_Tutor.exe"
    if not exe_path.exists():
        raise RuntimeError(f"Expected executable not found at {exe_path}")
    print(f"[OK] Binary compiled successfully: {exe_path}")


def prepare_clean_slate_data() -> None:
    """Ensure clean-slate database, model weights, and knowledge data in DIST_DIR."""
    print("=" * 60)
    print("  [2/5] Assembling Clean-Slate Data & Knowledge Bundles...")
    print("=" * 60)

    # Clean data dir
    data_dir = DIST_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize clean-slate SQLite database
    db_path = data_dir / "gayatri.db"
    if db_path.exists():
        db_path.unlink()

    for stale_file in ("student_profile.json", "events.jsonl", "settings.json"):
        stale_p = data_dir / stale_file
        if stale_p.exists():
            stale_p.unlink()

    from core.session import SessionStore
    store = SessionStore(db_path=db_path)
    store.close()
    print(f"[OK] Initialized clean-slate SQLite DB at {db_path} (0 messages)")

    # Models directory
    models_dir = DIST_DIR / "models" / "gayatri"
    models_dir.mkdir(parents=True, exist_ok=True)

    # Detect 3B model file
    possible_models = [
        PROJECT_ROOT / "GayatriAI" / "models" / "gayatri" / "Gayatri-Tutor-v3-Q4_K_M.gguf",
        Path.home() / "AppData" / "Local" / "GayatriAI" / "models" / "gayatri" / "Gayatri-Tutor-v3-Q4_K_M.gguf",
        Path.home() / "Downloads" / "Gayatri-Tutor-v3-Q4_K_M.gguf",
    ]

    model_src = None
    for p in possible_models:
        if p.exists() and p.stat().st_size > 1024 * 1024 * 500:
            model_src = p
            break

    if model_src:
        dest_model = models_dir / "Gayatri-Tutor-v3-Q4_K_M.gguf"
        if not dest_model.exists() or dest_model.stat().st_size != model_src.stat().st_size:
            print(f"[*] Copying fine-tuned 3B model from {model_src} ({model_src.stat().st_size / 1024**3:.2f} GB)...")
            shutil.copy2(model_src, dest_model)
            print(f"[OK] Model bundled at {dest_model}")
        else:
            print(f"[OK] Model already present at {dest_model}")
    else:
        print("[WARN] Model file 'Gayatri-Tutor-v3-Q4_K_M.gguf' not found in local cache.")
        print("       The directory models/gayatri/ is created and ready for model placement.")

    # Copy RAG data and Curriculum data into dist/data
    rag_src = PROJECT_ROOT / "data" / "rag"
    if rag_src.exists():
        rag_dest = data_dir / "rag"
        if rag_dest.exists():
            shutil.rmtree(rag_dest)
        shutil.copytree(rag_src, rag_dest)
        print(f"[OK] Bundled NCERT RAG data at {rag_dest}")

    curriculum_src = PROJECT_ROOT / "data" / "curriculum"
    if curriculum_src.exists():
        curriculum_dest = data_dir / "curriculum"
        if curriculum_dest.exists():
            shutil.rmtree(curriculum_dest)
        shutil.copytree(curriculum_src, curriculum_dest)
        print(f"[OK] Bundled Curriculum data at {curriculum_dest}")

    # Copy app/ui to dist/app/ui
    ui_src = PROJECT_ROOT / "app" / "ui"
    if ui_src.exists():
        ui_dest = DIST_DIR / "app" / "ui"
        if ui_dest.exists():
            shutil.rmtree(ui_dest)
        shutil.copytree(ui_src, ui_dest)
        print(f"[OK] Bundled UI assets at {ui_dest}")

    # Copy Evaluator Guide and Icons
    for fname in ("EVALUATION_GUIDE.md", "gai3.ico", "gai3.png"):
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy2(src, DIST_DIR / fname)

    # Ensure no .py files leaked into dist
    leaked_py = list(DIST_DIR.rglob("*.py"))
    if leaked_py:
        print(f"[WARN] Removing {len(leaked_py)} plaintext .py files from dist to enforce anti-reverse-engineering...")
        for p in leaked_py:
            p.unlink()


def create_portable_zip() -> Path:
    """Create release_staging/Gayatri_Chemistry_Tutor_Portable_v3.0.0.zip."""
    print("=" * 60)
    print("  [3/5] Packaging 1-Click Portable ZIP...")
    print("=" * 60)
    RELEASE_STAGING.mkdir(parents=True, exist_ok=True)
    zip_path = RELEASE_STAGING / "Gayatri_Chemistry_Tutor_Portable_v3.0.0.zip"

    if zip_path.exists():
        zip_path.unlink()

    print(f"[*] Compressing {DIST_DIR} into {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(DIST_DIR):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(DIST_DIR.parent)
                zf.write(full_path, arcname=str(rel_path))

    size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"[OK] Portable ZIP created: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def compile_inno_setup() -> Path | None:
    """Compile Inno Setup script if ISCC.exe is available."""
    print("=" * 60)
    print("  [4/5] Checking Inno Setup Compiler...")
    print("=" * 60)

    iscc_candidates = [
        shutil.which("iscc"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
    ]

    iscc_path = None
    for cand in iscc_candidates:
        if cand and Path(cand).exists():
            iscc_path = Path(cand)
            break

    iss_file = PROJECT_ROOT / "packaging" / "installer.iss"
    if not iscc_path:
        print("[INFO] Inno Setup (ISCC.exe) not found on PATH.")
        print("       To build the setup installer, run: winget install JR.InnoSetup")
        print("       Then re-run this script.")
        return None

    print(f"[*] Found Inno Setup at {iscc_path}")
    print(f"[*] Compiling {iss_file}...")
    cmd = [str(iscc_path), str(iss_file)]
    subprocess.check_call(cmd, cwd=PROJECT_ROOT / "packaging")

    setup_exe = RELEASE_STAGING / "Gayatri_Chemistry_Tutor_v3_Setup.exe"
    if setup_exe.exists():
        size_mb = setup_exe.stat().st_size / 1024 / 1024
        print(f"[OK] Setup Installer created: {setup_exe} ({size_mb:.1f} MB)")
        return setup_exe
    return None


def generate_checksums() -> Path:
    """Generate SHA256SUMS.txt for all files in release_staging/."""
    print("=" * 60)
    print("  [5/5] Generating Cryptographic SHA-256 Checksums...")
    print("=" * 60)

    checksum_file = RELEASE_STAGING / "SHA256SUMS.txt"
    lines = []

    # Copy markdown guides into staging as well
    for doc in ("EVALUATION_GUIDE.md", "RELEASE_NOTES_v3.0.0.md"):
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, RELEASE_STAGING / doc)

    # Stage standalone GGUF model for direct access
    bundled_model = DIST_DIR / "models" / "gayatri" / "Gayatri-Tutor-v3-Q4_K_M.gguf"
    if bundled_model.exists():
        staged_model = RELEASE_STAGING / "Gayatri-Tutor-v3-Q4_K_M.gguf"
        if not staged_model.exists():
            try:
                os.link(bundled_model, staged_model)
                print(f"[OK] Staged standalone model asset via hardlink: {staged_model.name}")
            except Exception:
                shutil.copy2(bundled_model, staged_model)
                print(f"[OK] Staged standalone model asset via copy: {staged_model.name}")

    for item in sorted(RELEASE_STAGING.glob("*")):
        if item.is_file() and item.name != "SHA256SUMS.txt":
            sha = compute_sha256(item)
            lines.append(f"{sha}  {item.name}")
            print(f"  {item.name}: {sha[:16]}...")

    checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] Checksums written to {checksum_file}")
    return checksum_file


def main():
    print("============================================================")
    print("  GAYATRI CHEMISTRY TUTOR — Master Release Builder")
    print("  Target: https://github.com/Gayatri-Education/Gayatri-Tutor-ChemistryDemo")
    print("============================================================\n")

    ensure_pyinstaller()
    build_pyinstaller()
    prepare_clean_slate_data()
    create_portable_zip()
    compile_inno_setup()
    generate_checksums()

    print("\n" + "=" * 60)
    print("  RELEASE BUILD COMPLETE!")
    print(f"  Deliverables staged in: {RELEASE_STAGING}")
    print("============================================================")


if __name__ == "__main__":
    main()
