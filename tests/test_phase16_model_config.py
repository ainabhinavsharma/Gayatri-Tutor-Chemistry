"""Tests for Phase 16: Model Manifest & Config Re-Audit (P13-T01 to P13-T03)."""
import json
import pytest
from core.model_fetch.manifest_validator import load_and_validate_manifest, ModelManifestValidationError


def test_root_model_manifest_valid():
    """Test that the root model_manifest.json is valid."""
    data = load_and_validate_manifest("model_manifest.json")
    assert data["model_name"] == "gayatri-chemistry-tutor-v1"
    assert data["context_length"] == 8192
    assert "sha256" in data


def test_missing_manifest_file(tmp_path):
    """Test raising error when manifest file is missing."""
    missing_path = tmp_path / "non_existent_manifest.json"
    with pytest.raises(ModelManifestValidationError, match="not found"):
        load_and_validate_manifest(missing_path)


def test_malformed_json_manifest(tmp_path):
    """Test raising error on malformed JSON content."""
    bad_json_path = tmp_path / "bad_manifest.json"
    bad_json_path.write_text("{invalid_json: true", encoding="utf-8")

    with pytest.raises(ModelManifestValidationError, match="Failed to parse"):
        load_and_validate_manifest(bad_json_path)


def test_missing_required_keys(tmp_path):
    """Test raising error when required manifest keys are missing."""
    incomplete_manifest = {
        "model_name": "gayatri-v1",
        "base_model": "Qwen2.5-7B",
        # Missing adapter, quantization, context_length, training_dataset_version, created_at, sha256
    }
    path = tmp_path / "incomplete_manifest.json"
    path.write_text(json.dumps(incomplete_manifest), encoding="utf-8")

    with pytest.raises(ModelManifestValidationError, match="missing required keys"):
        load_and_validate_manifest(path)


def test_invalid_context_length(tmp_path):
    """Test raising error when context_length is non-integer or <= 0."""
    manifest = {
        "model_name": "gayatri-v1",
        "base_model": "Qwen2.5-7B",
        "adapter": "adapter-v1",
        "quantization": "Q4_K_M",
        "context_length": -1,
        "training_dataset_version": "v1.0",
        "created_at": "2026-09-19T00:00:00Z",
        "sha256": "abcdef123456",
    }
    path = tmp_path / "invalid_context.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ModelManifestValidationError, match="Invalid context_length"):
        load_and_validate_manifest(path)
