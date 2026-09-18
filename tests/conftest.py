"""Gayatri AI — Test configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

# Ensure core module can be imported
sys_path = str(Path(__file__).resolve().parent.parent)
import sys

if sys_path not in sys.path:
    sys.path.insert(0, sys_path)


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect all data to a temp directory for each test and reset singletons."""
    monkeypatch.setenv("GAYATRI_DATA_DIR", str(tmp_path))

    import core.config as cfg
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "gayatri.db")
    monkeypatch.setattr(cfg, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(cfg, "MODELS_DIR", tmp_path / "models" / "gayatri")
    monkeypatch.setattr(cfg, "LOG_DIR", tmp_path / "logs")

    # Reset in-memory global singletons so tests are cleanly isolated
    import core.session as sess
    sess._session_store = None

    import core.orchestrator as orch
    orch._ldg = None
    orch._tutor_engine = None

    import core.tutor_engine as tutor
    tutor.reset_tutor_engine()

    yield

    sess._session_store = None
    orch._ldg = None
    orch._tutor_engine = None
    tutor.reset_tutor_engine()
