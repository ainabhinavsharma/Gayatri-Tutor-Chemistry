#!/usr/bin/env python3
"""Gayatri AI — Generate gai3.ico and Windows desktop / project launch shortcuts.

1. Generates high-quality gai3.ico from gai3.png using PySide6.
2. Creates Windows .lnk shortcuts:
   - In workspace: 'Gayatri Chemistry Tutor.lnk'
   - On User Desktop: 'Gayatri Chemistry Tutor.lnk'
   Both pointing to run_student_demo.bat with gai3.ico as icon.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_ico() -> Path:
    """Generate gai3.ico from gai3.png using PySide6."""
    png_path = PROJECT_ROOT / "gai3.png"
    if not png_path.exists():
        raise FileNotFoundError(f"Source image not found at {png_path}")

    ico_path = PROJECT_ROOT / "gai3.ico"

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage

    src_img = QImage(str(png_path))
    if src_img.isNull():
        raise ValueError(f"Failed to load image from {png_path}")

    # Scale to 256x256 with smooth transformation and save as ICO
    scaled = src_img.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    success = scaled.save(str(ico_path), "ICO")
    if not success:
        raise RuntimeError("Failed to save gai3.ico")

    # Also copy gai3.png and gai3.ico into app/ui for WebEngine access
    ui_dir = PROJECT_ROOT / "app" / "ui"
    if ui_dir.exists():
        shutil.copy2(png_path, ui_dir / "gai3.png")
        shutil.copy2(ico_path, ui_dir / "gai3.ico")

    print(f"[OK] Generated gai3.ico at {ico_path}")
    return ico_path


def create_windows_shortcuts(ico_path: Path) -> None:
    """Create .lnk shortcuts using VBScript."""
    bat_path = PROJECT_ROOT / "run_student_demo.bat"
    if not bat_path.exists():
        raise FileNotFoundError(f"Launch batch file not found at {bat_path}")

    # Locations to create shortcuts
    project_lnk = PROJECT_ROOT / "Gayatri Chemistry Tutor.lnk"
    desktop_lnk = Path.home() / "Desktop" / "Gayatri Chemistry Tutor.lnk"

    vbs_content = f'''
Set oWS = CreateObject("WScript.Shell")

' 1. Project Folder Shortcut
Set oLink1 = oWS.CreateShortcut("{project_lnk}")
oLink1.TargetPath = "{bat_path}"
oLink1.WorkingDirectory = "{PROJECT_ROOT}"
oLink1.IconLocation = "{ico_path},0"
oLink1.Description = "Gayatri Chemistry Tutor — NCERT Adaptive Learning"
oLink1.WindowStyle = 1
oLink1.Save

' 2. Desktop Shortcut
Set oLink2 = oWS.CreateShortcut("{desktop_lnk}")
oLink2.TargetPath = "{bat_path}"
oLink2.WorkingDirectory = "{PROJECT_ROOT}"
oLink2.IconLocation = "{ico_path},0"
oLink2.Description = "Gayatri Chemistry Tutor — NCERT Adaptive Learning"
oLink2.WindowStyle = 1
oLink2.Save
'''

    temp_vbs = PROJECT_ROOT / "_temp_create_shortcuts.vbs"
    try:
        temp_vbs.write_text(vbs_content, encoding="utf-8")
        result = subprocess.run(["cscript", "//nologo", str(temp_vbs)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[WARN] VBScript warning: {result.stderr or result.stdout}")
        else:
            print(f"[OK] Created project shortcut: {project_lnk}")
            print(f"[OK] Created desktop shortcut: {desktop_lnk}")
    finally:
        if temp_vbs.exists():
            temp_vbs.unlink(missing_ok=True)


def main():
    print("=" * 60)
    print("  GAYATRI CHEMISTRY TUTOR — Icon & Shortcut Generator")
    print("=" * 60)
    ico_path = generate_ico()
    if sys.platform == "win32":
        create_windows_shortcuts(ico_path)
    print("Done! You can now double click 'Gayatri Chemistry Tutor.lnk' to launch.")


if __name__ == "__main__":
    main()
