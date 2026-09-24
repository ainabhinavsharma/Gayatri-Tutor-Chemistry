# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for Gayatri Chemistry Tutor v3.0.1.

Fixes vs v3.0.0:
  - llama_cpp DLL loading via runtime hook (LLAMA_CPP_LIB_PATH)
  - Removed PRIVATE_WORK from datas (private IP not shipped)
  - Added atomic RAG data/rag/atomic/ to datas
  - Added training/prompts/ to datas (SLM system prompt contract)
  - Added app/windows/splash_screen to hiddenimports
  - Added app/bridge/provider to hiddenimports
  - Added core.rag.retriever, core.tutor.memory to hiddenimports
  - Added runtime hook for llama_cpp DLL path resolution
  - opengl32sw.dll excluded (software renderer not needed for Qt WebEngine)
  - scipy, torch, sentence_transformers excluded (not used in frozen SLM path)
"""

import sys
from pathlib import Path

block_cipher = None
SPEC_ROOT = Path(SPECPATH).resolve() if 'SPECPATH' in globals() else Path('.').resolve()
PROJECT_ROOT = SPEC_ROOT.parent if SPEC_ROOT.name == 'packaging' else SPEC_ROOT

datas = [
    # Core UI assets
    (str(PROJECT_ROOT / 'app' / 'ui'), 'app/ui'),
    # RAG knowledge base (main + atomic cards)
    (str(PROJECT_ROOT / 'data' / 'rag'), 'data/rag'),
    # Branding
    (str(PROJECT_ROOT / 'gai3.ico'), '.'),
    (str(PROJECT_ROOT / 'gai3.png'), '.'),
    # User-facing docs
    (str(PROJECT_ROOT / 'EVALUATION_GUIDE.md'), '.'),
    # SLM system prompt contracts (needed by PromptContractLoader at runtime)
    (str(PROJECT_ROOT / 'training' / 'prompts'), 'training/prompts'),
]

# NOTE: PRIVATE_WORK is intentionally excluded (private IP, not for distribution)

# Ensure llama_cpp binaries are collected (belt-and-suspenders alongside hook)
binaries = []
try:
    import llama_cpp
    llama_dir = Path(llama_cpp.__file__).parent
    # Collect lib/*.dll explicitly
    for dll in (llama_dir / 'lib').glob('*.dll'):
        binaries.append((str(dll), 'llama_cpp/lib'))
    for so in (llama_dir / 'lib').glob('*.so*'):
        binaries.append((str(so), 'llama_cpp/lib'))
except Exception as e:
    print(f"[WARN] Could not inspect llama_cpp lib DLLs: {e}")

hiddenimports = [
    # Qt6 WebEngine (must be explicit for PyInstaller)
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebChannel',
    'PySide6.QtWidgets',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtNetwork',
    # Python stdlib
    'sqlite3',
    'queue',
    'ctypes',
    'ctypes.wintypes',
    # Core app modules
    'core.config',
    'core.session',
    'core.hardware',
    'core.curriculum.resolver',
    'core.tutor.controller',
    'core.tutor.adaptive',
    'core.tutor.memory',
    'core.runtimes.chemistry',
    'core.runtimes.general',
    'core.providers.local',
    'core.learning.progress',
    'core.rag.retriever',
    'core.prompts.loader',
    'core.security.guardrails',
    'core.security.validation',
    'core.security.cache',
    # App bridges and windows
    'app.bridge.facade',
    'app.bridge.chat',
    'app.bridge.model',
    'app.bridge.provider',
    'app.bridge.settings',
    'app.bridge.window',
    'app.windows.main_window',
    'app.windows.splash_screen',
]

excludes = [
    # Dev/test tools (never in production)
    'pytest',
    '_pytest',
    'unittest',
    'tkinter',
    'IPython',
    'notebook',
    # Heavy ML libs not needed for SLM GGUF inference
    'torch',
    'torchvision',
    'torchaudio',
    'transformers',
    'accelerate',
    'peft',
    'datasets',
    'sentence_transformers',
    'sklearn',
    'scipy',
    'matplotlib',
    'PIL',
    'cv2',
    # HuggingFace (download infra, not needed in frozen app)
    'huggingface_hub',
    'hf_xet',
    'safetensors',
    # Training-only deps
    'bitsandbytes',
    'trl',
]

a = Analysis(
    [str(PROJECT_ROOT / 'app' / 'main.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],                          # our custom hooks/ dir
    hooksconfig={},
    runtime_hooks=['hooks/rthook-llama_cpp.py'],  # runs BEFORE any import
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
    upx=False,                  # UPX disabled: causes false-positive AV detections
    console=False,              # Windowed GUI, no terminal popup
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
    upx=False,
    upx_exclude=[],
    name='Gayatri_Chemistry_Tutor',
)
