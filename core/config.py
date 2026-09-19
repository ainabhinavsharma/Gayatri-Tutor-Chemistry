"""Gayatri AI — Core configuration.

All constants, paths, and feature flags live here.
No hardcoding anywhere else in the codebase.
"""

from __future__ import annotations

import os
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
    return Path(os.environ.get("LOCALAPPDATA", ".")) / "GayatriAI"


def _project_root() -> Path:
    """Root of the source tree."""
    return Path(__file__).resolve().parent.parent


BASE_DIR: Path = _project_root()
DATA_DIR: Path = _data_dir()
MODELS_DIR: Path = DATA_DIR / "models" / "gayatri"
RAG_DIR: Path = DATA_DIR / "rag"
COURSES_DIR: Path = DATA_DIR / "courses"
DB_PATH: Path = DATA_DIR / "gayatri.db"
SETTINGS_PATH: Path = DATA_DIR / "settings.json"
LOG_DIR: Path = DATA_DIR / "logs"
HMAC_KEY_PATH: Path = DATA_DIR / ".hmac_key"

# Ensure dirs exist at import time (idempotent)
for d in (DATA_DIR, MODELS_DIR, RAG_DIR, COURSES_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ── Model configuration ────────────────────────────────────────────────

# Primary local model (fine-tuned GGUF)
# Place your downloaded GGUF file in MODELS_DIR and set LOCAL_MODEL_FILE to match the filename
# Training notebook outputs: gayatri-Q4_K_M.gguf (~500MB, Q4_K_M quantized gemma-2-2b-it)
LOCAL_MODEL_FILE: str = "Gayatri-Tutor-v3-Q4_K_M.gguf"
_PROJECT_MODEL_DIR: Path = BASE_DIR / "GayatriAI" / "models" / "gayatri"
LOCAL_MODEL_DIR: Path = _PROJECT_MODEL_DIR if (_PROJECT_MODEL_DIR / LOCAL_MODEL_FILE).exists() and not (MODELS_DIR / LOCAL_MODEL_FILE).exists() else MODELS_DIR

LOCAL_MODEL_CONTEXT: int = 8192
LOCAL_MODEL_GPU_LAYERS: int = -1  # -1 = all layers on GPU if available

# Model download source (HuggingFace bartowski GGUF — used by download_model in bridge)
MODEL_HUGGINGFACE_REPO: str = "bartowski/gemma-2-2b-it-GGUF"
MODEL_GGUF_FILENAME: str = "gemma-2-2b-it-IQ3_M.gguf"

# Inference defaults
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 512
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
