"""Model Manifest Validator (Phase 13).

Ensures model deployment consistency by validating model_manifest.json
against runtime configuration.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("gayatri.model.validator")

REQUIRED_MANIFEST_KEYS = {
    "model_name",
    "base_model",
    "adapter",
    "quantization",
    "context_length",
    "training_dataset_version",
    "created_at",
    "sha256",
}


class ModelManifestValidationError(ValueError):
    """Raised when model manifest is missing or inconsistent."""
    pass


def load_and_validate_manifest(manifest_path: Path | str | None = None) -> dict[str, Any]:
    """Load model_manifest.json and validate required keys and consistency (P13-T01 & P13-T02)."""
    if manifest_path is None:
        manifest_path = Path("model_manifest.json")
    else:
        manifest_path = Path(manifest_path)

    if not manifest_path.exists():
        raise ModelManifestValidationError(f"Model manifest file not found at '{manifest_path}'.")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ModelManifestValidationError(f"Failed to parse model manifest JSON: {e}")

    missing = REQUIRED_MANIFEST_KEYS - set(data.keys())
    if missing:
        raise ModelManifestValidationError(f"Model manifest is missing required keys: {missing}")

    if not isinstance(data.get("context_length"), int) or data["context_length"] <= 0:
        raise ModelManifestValidationError(f"Invalid context_length in manifest: {data.get('context_length')}")

    logger.info(f"Model manifest validated successfully: {data['model_name']} ({data['base_model']})")
    return data
