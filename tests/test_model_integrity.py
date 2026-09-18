"""Tests for MODEL-001 (Integrity/safety), MODEL-002 (Allowlist), and MODEL-003 (Compatibility)."""

import pytest
from pathlib import Path
from core.model_fetch.ollama_pull import (
    validate_model_allowlist,
    validate_hardware_compatibility,
    OllamaPullError,
    pull_model,
)


def test_model_allowlist_enforcement():
    """MODEL-002: Verify approved models pass and unapproved models raise OllamaPullError."""
    # Approved models
    validate_model_allowlist("DBERT", "DBERT_AI")
    validate_model_allowlist("library", "gemma2")

    # Unapproved models
    with pytest.raises(OllamaPullError) as exc_info:
        validate_model_allowlist("evil_namespace", "malicious_model")
    assert "not in the approved model allowlist" in str(exc_info.value)


def test_destination_allowlist_rejection(tmp_path: Path):
    """MODEL-001: Attempting to pull into a destination path with parent traversal is blocked."""
    outside_dir = tmp_path / "sub" / ".." / "escape"

    with pytest.raises(OllamaPullError) as exc_info:
        pull_model(
            namespace="DBERT",
            name="DBERT_AI",
            tag="latest",
            dest_dir=outside_dir,
        )
    assert "contains path traversal" in str(exc_info.value)


def test_hardware_compatibility_check(monkeypatch):
    """MODEL-003: If available RAM is insufficient for the model, fail preflight validation."""
    from collections import namedtuple
    Mem = namedtuple("Mem", ["ram_free_mb"])

    # Simulate only 100MB free RAM
    monkeypatch.setattr("core.hardware.detect_hardware", lambda: Mem(ram_free_mb=100))

    ok, msg = validate_hardware_compatibility(size_bytes=2 * 1024 * 1024 * 1024)  # 2 GB model
    assert ok is False
    assert "Insufficient free RAM" in msg

    # Simulate 8000MB free RAM
    monkeypatch.setattr("core.hardware.detect_hardware", lambda: Mem(ram_free_mb=8000))
    ok, msg = validate_hardware_compatibility(size_bytes=2 * 1024 * 1024 * 1024)
    assert ok is True
    assert msg == "OK"
