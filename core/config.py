"""Gayatri AI — Core configuration.

All constants, paths, and feature flags live here.
No hardcoding anywhere else in the codebase.
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path


class ExecutionMode(str, Enum):
    """Execution mode for privacy enforcement."""
    LOCAL_ONLY = "local_only"       # Data never leaves the device
    CLOUD_ALLOWED = "cloud_allowed" # Cloud providers may be used (explicit opt-in)


# ── Paths ──────────────────────────────────────────────────────────────

def _data_dir() -> Path:
    """Runtime data directory. Overridable via GAYATRI_DATA_DIR env var."""
    override = os.environ.get("GAYATRI_DATA_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "data").exists():
            return exe_dir / "data"
    return Path(os.environ.get("LOCALAPPDATA", ".")) / "GayatriAI"


def _project_root() -> Path:
    """Root of the source tree or frozen application bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR: Path = _project_root()
DATA_DIR: Path = _data_dir()
MODELS_DIR: Path = DATA_DIR / "models" / "gayatri"
RAG_DIR: Path = DATA_DIR / "rag"
COURSES_DIR: Path = DATA_DIR / "courses"
DB_PATH: Path = DATA_DIR / "gayatri.db"
SETTINGS_PATH: Path = DATA_DIR / "settings.json"
LOG_DIR: Path = DATA_DIR / "logs"
UPLOADS_DIR: Path = DATA_DIR / "uploads"
HMAC_KEY_PATH: Path = DATA_DIR / ".hmac_key"

# Ensure dirs exist at import time (idempotent)
for d in (DATA_DIR, MODELS_DIR, RAG_DIR, COURSES_DIR, LOG_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ── Model configuration ────────────────────────────────────────────────

# Primary local model locations
_PROJECT_MODEL_DIR: Path = BASE_DIR / "GayatriAI" / "models" / "gayatri"
_PORTABLE_MODEL_DIR: Path = BASE_DIR / "models" / "gayatri"
_DOWNLOADS_MODEL_DIR: Path = Path.home() / "Downloads"

def _get_model_search_dirs() -> tuple[Path, ...]:
    dirs = [_PORTABLE_MODEL_DIR, _PROJECT_MODEL_DIR, MODELS_DIR]
    if _DOWNLOADS_MODEL_DIR.exists():
        dirs.append(_DOWNLOADS_MODEL_DIR)
    return tuple(dirs)

def _detect_initial_model_file() -> str:
    env_override = os.environ.get("GAYATRI_MODEL_FILE")
    if env_override:
        return env_override
    # Default to 3B Qwen2.5 model
    v3_name = "Gayatri-Tutor-v3-Q4_K_M.gguf"
    for d in _get_model_search_dirs():
        if (d / v3_name).exists():
            return v3_name
    return v3_name

LOCAL_MODEL_FILE: str = _detect_initial_model_file()

def _get_best_model_dir() -> Path:
    for d in _get_model_search_dirs():
        if (d / LOCAL_MODEL_FILE).exists():
            return d
    return _PORTABLE_MODEL_DIR if _PORTABLE_MODEL_DIR.exists() else MODELS_DIR

LOCAL_MODEL_DIR: Path = _get_best_model_dir()

def get_active_model_path() -> Path:
    """Return the absolute path to the currently active GGUF model."""
    global LOCAL_MODEL_FILE, LOCAL_MODEL_DIR
    for d in _get_model_search_dirs():
        if (d / LOCAL_MODEL_FILE).exists():
            LOCAL_MODEL_DIR = d
            return d / LOCAL_MODEL_FILE
    LOCAL_MODEL_DIR = _PORTABLE_MODEL_DIR if _PORTABLE_MODEL_DIR.exists() else MODELS_DIR
    return LOCAL_MODEL_DIR / LOCAL_MODEL_FILE

def set_active_model_file(filename: str) -> Path:
    """Switch the active local GGUF model filename."""
    global LOCAL_MODEL_FILE, LOCAL_MODEL_DIR
    LOCAL_MODEL_FILE = filename
    return get_active_model_path()

def list_installed_models() -> list[dict]:
    """Scan all model directories for available GGUF files."""
    found: dict[str, Path] = {}
    active_path = get_active_model_path()
    for d in _get_model_search_dirs():
        if d.exists():
            for p in d.glob("*.gguf"):
                if p.is_file() and p.stat().st_size > 1024 * 1024:
                    found[p.name] = p
    results = []
    for name, path in sorted(found.items()):
        size_mb = round(path.stat().st_size / (1024 * 1024), 1)
        results.append({
            "filename": name,
            "size_mb": size_mb,
            "active": (name == active_path.name),
            "path": str(path),
        })
    return results

LOCAL_MODEL_CONTEXT: int = 8192
LOCAL_MODEL_GPU_LAYERS: int = -1  # -1 = all layers on GPU if available

# Model download source (HuggingFace bartowski GGUF — used by download_model in bridge)
MODEL_HUGGINGFACE_REPO: str = "bartowski/gemma-2-2b-it-GGUF"
MODEL_GGUF_FILENAME: str = "gemma-2-2b-it-IQ3_M.gguf"

# Inference defaults
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 1024
DEFAULT_TOP_P: float = 0.9
DEFAULT_TOP_K: int = 40


# ── Agent system ───────────────────────────────────────────────────────

MAX_AGENT_STEPS: int = 12       # max tool-call iterations per turn
AGENT_TIMEOUT_S: int = 60       # max time for agent to complete
TOOL_ARG_MAX_STRING_LENGTH: int = 4096  # max string length for tool arguments


# ── Security ───────────────────────────────────────────────────────────

MAX_INPUT_CHARS: int = 32_000
MAX_INPUT_TOKENS: int = 8_000
MAX_CONCURRENT_REQUESTS: int = 4

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MIN: int = 30
RATE_LIMIT_WINDOW_S: int = 60

# Cost tracking (USD per 1K tokens)
COST_WARN_USD_PER_DAY: float = 2.0
COST_CAP_USD_PER_DAY: float = 10.0

# Sandbox
SANDBOX_WALL_TIMEOUT_S: int = 30
SANDBOX_MEMORY_BYTES: int = 256 * 1024 * 1024  # 256 MB
SANDBOX_MAX_OUTPUT_BYTES: int = 1 * 1024 * 1024  # 1 MB
SANDBOX_MAX_PROCESSES: int = 1
CODE_MENTOR_MAX_CODE_CHARS: int = 10_000
CODE_MENTOR_MAX_HIDDEN_TESTS: int = 10


# ── RAG ────────────────────────────────────────────────────────────────

RAG_CHUNK_SIZE: int = 512
RAG_OVERLAP: int = 64
RAG_RRF_K: int = 60
RAG_TOP_K: int = 5
RAG_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
RAG_EMBEDDING_DIM: int = 384


# ── Tutor engine ────────────────────────────────────────────────────────

BKT_SLIP: float = 0.1
BKT_GUESS: float = 0.1
BKT_LEARN: float = 0.3
BKT_PRIOR: float = 0.5
BKT_DECAY_PER_DAY: float = 0.98
MASTERY_UNLOCK_THRESHOLD: float = 0.85
PRACTICE_TARGET_SUCCESS: float = 0.75

# Learning Dependency Graph
LDG_MASTERY_THRESHOLD: float = 0.85   # mastery >= this → concept unlocked
LDG_INITIAL_MASTERY: float = 0.3      # starting mastery for new concepts
LDG_LEARN_RATE: float = 0.15          # mastery increase on correct answer
LDG_DECAY_RATE: float = 0.05          # mastery decrease on wrong answer
LDG_MAX_CONCEPTS: int = 200           # safety limit
LDG_CURICULUM_DIR: Path = BASE_DIR / "data" / "curriculum"


# ── Logging ─────────────────────────────────────────────────────────────

LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: int = 5


# ── UI ──────────────────────────────────────────────────────────────────

WINDOW_WIDTH: int = 1100
WINDOW_HEIGHT: int = 720
WINDOW_MIN_WIDTH: int = 800
WINDOW_MIN_HEIGHT: int = 600
FEATURE_FLAGS = {
    "enable_legacy_agents": False
}
