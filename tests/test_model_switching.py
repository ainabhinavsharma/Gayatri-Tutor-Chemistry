"""Tests for dynamic model discovery, switching, and bridge exposure."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core import config
from core.providers.local import LocalProvider
from app.bridge.facade import Bridge


def test_core_config_list_installed_models(tmp_path, monkeypatch):
    """Test discovering multiple .gguf models in models directory."""
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(config, "_PROJECT_MODEL_DIR", tmp_path / "project_models")
    
    (tmp_path / "models").mkdir(parents=True, exist_ok=True)
    (tmp_path / "project_models").mkdir(parents=True, exist_ok=True)

    # Create dummy models (need to be > 1MB)
    m1 = tmp_path / "models" / "Gayatri-Tutor-v3-Q4_K_M.gguf"
    m2 = tmp_path / "project_models" / "Gayatri-Tutor-SLM-Q4_K_M.gguf"
    
    m1.write_bytes(b"0" * (1024 * 1024 + 100))
    m2.write_bytes(b"0" * (1024 * 1024 + 200))

    models = config.list_installed_models()
    filenames = [m["filename"] for m in models]
    assert "Gayatri-Tutor-v3-Q4_K_M.gguf" in filenames
    assert "Gayatri-Tutor-SLM-Q4_K_M.gguf" in filenames


def test_local_provider_switch_model(tmp_path, monkeypatch):
    """Test switching active model clears model lock and updates path."""
    test_models = tmp_path / "models"
    test_models.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "MODELS_DIR", test_models)
    monkeypatch.setattr(config, "_PROJECT_MODEL_DIR", test_models)

    m1 = test_models / "model_alpha.gguf"
    m1.write_bytes(b"0" * (1024 * 1024 + 50))

    res = LocalProvider.switch_model("model_alpha.gguf")
    assert res["ok"] is True
    assert res["active_model"] == "model_alpha.gguf"
    assert LocalProvider.MODEL_PATH.name == "model_alpha.gguf"
    assert LocalProvider._model is None


def test_bridge_get_available_models(monkeypatch):
    """Test bridge slot get_available_models returns valid JSON."""
    bridge = Bridge()
    dummy_models = [
        {"filename": "model_a.gguf", "size_mb": 350.5, "active": True, "path": "/path/a"},
        {"filename": "model_b.gguf", "size_mb": 1900.0, "active": False, "path": "/path/b"},
    ]
    monkeypatch.setattr(LocalProvider, "list_available_models", lambda: dummy_models)

    raw = bridge.get_available_models()
    data = json.loads(raw)
    assert data["ok"] is True
    assert len(data["models"]) == 2
    assert data["models"][0]["filename"] == "model_a.gguf"


def test_bridge_set_active_model_success(monkeypatch):
    """Test bridge slot set_active_model when idle."""
    bridge = Bridge()
    bridge._generation_active = False

    monkeypatch.setattr(
        LocalProvider,
        "switch_model",
        lambda name: {"ok": True, "active_model": name, "path": f"/models/{name}", "exists": True}
    )

    raw = bridge.set_active_model("Gayatri-Tutor-v3-Q4_K_M.gguf")
    data = json.loads(raw)
    assert data["ok"] is True
    assert data["active_model"] == "Gayatri-Tutor-v3-Q4_K_M.gguf"


def test_bridge_set_active_model_blocked_during_generation():
    """Test bridge slot set_active_model returns error if generation is active."""
    bridge = Bridge()
    bridge._generation_active = True

    raw = bridge.set_active_model("some_model.gguf")
    data = json.loads(raw)
    assert data["ok"] is False
    assert "generating" in data["error"].lower()
