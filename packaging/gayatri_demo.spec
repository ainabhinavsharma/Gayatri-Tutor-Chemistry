# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for Gayatri Chemistry Tutor (Demo Release).

Produces a standalone, frozen binary distribution with gai3.ico branding,
PySide6 Qt6 WebEngine, llama.cpp C++ runtime, and offline NCERT RAG data.
Zero plaintext .py source files are exposed.
"""

import sys
from pathlib import Path

block_cipher = None
SPEC_ROOT = Path(SPECPATH).resolve() if 'SPECPATH' in globals() else Path('.').resolve()
PROJECT_ROOT = SPEC_ROOT.parent if SPEC_ROOT.name == 'packaging' else SPEC_ROOT

datas = [
    (str(PROJECT_ROOT / 'app' / 'ui'), 'app/ui'),
    (str(PROJECT_ROOT / 'data' / 'rag'), 'data/rag'),
    (str(PROJECT_ROOT / 'gai3.ico'), '.'),
    (str(PROJECT_ROOT / 'gai3.png'), '.'),
    (str(PROJECT_ROOT / 'EVALUATION_GUIDE.md'), '.'),
]

# Include learning graph definitions if present
prereq_dir = PROJECT_ROOT / 'PRIVATE_WORK' / 'learning_graph'
if prereq_dir.exists():
    datas.append((str(prereq_dir), 'PRIVATE_WORK/learning_graph'))

# Ensure llama_cpp binaries are collected
binaries = []
try:
    import llama_cpp
    llama_dir = Path(llama_cpp.__file__).parent
    for dll in llama_dir.glob("*.dll"):
        binaries.append((str(dll), 'llama_cpp'))
    for lib in llama_dir.glob("lib/*.dll"):
        binaries.append((str(lib), 'llama_cpp/lib'))
except Exception as e:
    print(f"[WARN] Could not automatically inspect llama_cpp DLLs: {e}")

hiddenimports = [
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebChannel',
    'PySide6.QtWidgets',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtNetwork',
    'sqlite3',
    'queue',
    'ctypes',
    'ctypes.wintypes',
    'core.config',
    'core.session',
    'core.hardware',
    'core.curriculum.resolver',
    'core.tutor.controller',
    'core.tutor.adaptive',
    'core.runtimes.chemistry',
    'core.runtimes.general',
    'core.providers.local',
    'core.learning.progress',
    'core.security.guardrails',
    'core.security.validation',
    'core.security.cache',
    'app.bridge.facade',
    'app.bridge.chat',
    'app.bridge.model',
    'app.bridge.settings',
    'app.bridge.window',
    'app.windows.main_window',
]

excludes = [
    'pytest',
    '_pytest',
    'unittest',
    'tkinter',
    'matplotlib',
    'IPython',
    'notebook',
    'scipy',
    'torch',
    'transformers',
    'accelerate',
    'peft',
    'datasets',
]

a = Analysis(
    [str(PROJECT_ROOT / 'app' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Gayatri_Chemistry_Tutor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed application (no terminal popup)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'gai3.ico'),
    version_info=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Gayatri_Chemistry_Tutor',
)
