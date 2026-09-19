"""Phase 13 Test Suite: Model and Configuration Consistency.

Verifies model_manifest.json presence, schema validation, and consistency checks (P13-T01 & P13-T02).
"""
import json
import pytest
import tempfile
from pathlib import Path

from core.model_fetch.manifest_validator import ModelManifestValidationError, load_and_validate_manifest


def test_root_model_manifest_valid():
    # Test repo root model_manifest.json
    manifest = load_and_validate_manifest("model_manifest.json")
    assert manifest["model_name"] == "gayatri-chemistry-tutor-v1"
    assert manifest["context_length"] == 8192
    assert "sha256" in manifest


def test_missing_key_validation():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        json.dump({"model_name": "test"}, tmp)
        tmp_path = tmp.name

    try:
        with pytest.raises(ModelManifestValidationError) as exc:
            load_and_validate_manifest(tmp_path)
        assert "missing required keys" in str(exc.value)
    finally:
        Path(tmp_path).unlink()
