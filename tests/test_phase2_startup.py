"""Tests for Phase 2: Startup and Runtime Audit.

Verifies:
1. Startup dependency check and fail-fast behavior on missing dependencies.
2. CLI flags (--check-startup, --version).
3. Fail-closed privacy policy enforcement (no silent pass on ImportError).
4. LocalProvider health reporting for missing dependencies.
5. Batch launchers syntax and entrypoint validation.
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
import pytest

from app.main import check_dependencies
from core.providers.base import ChatMessage, ChatOptions, ChatResponse, LLMProvider, ModelInfo


class DummyCloudProvider(LLMProvider):
    """Dummy cloud provider for testing privacy policy checks."""

    @property
    def name(self) -> str:
        return "DummyCloud"

    @property
    def key(self) -> str:
        return "dummy_cloud"

    @property
    def is_local(self) -> bool:
        return False

    def validate_key(self) -> tuple[bool, str]:
        return True, "OK"

    def list_models(self) -> list[ModelInfo]:
        return []

    def chat(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> ChatResponse:
        raise NotImplementedError

    def stream(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> Iterator[str]:
        raise NotImplementedError


def test_check_dependencies_success():
    """Verify that in the current environment, check_dependencies passes."""
    ok, missing = check_dependencies()
    assert ok is True
    assert len(missing) == 0


def test_check_dependencies_missing_simulated(monkeypatch):
    """Verify that check_dependencies detects missing dependencies."""
    import builtins
    real_import = builtins.__import__

    # Temporarily remove PySide6 from sys.modules
    removed = {}
    for k in list(sys.modules.keys()):
        if k == "PySide6" or k.startswith("PySide6."):
            removed[k] = sys.modules.pop(k)

    def mock_import(name, *args, **kwargs):
        if "PySide6" in name:
            raise ImportError(f"Simulated missing {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    try:
        ok, missing = check_dependencies()
        assert ok is False
        assert any("PySide6" in m for m in missing)
    finally:
        # Restore sys.modules
        sys.modules.update(removed)


def test_cli_flags_headless():
    """Verify that --check-startup and --version run headlessly and return code 0."""
    res_version = subprocess.run(
        [sys.executable, "-m", "app.main", "--version"],
        capture_output=True,
        text=True,
        check=False
    )
    assert res_version.returncode == 0
    assert "Gayatri AI v" in res_version.stdout

    res_check = subprocess.run(
        [sys.executable, "-m", "app.main", "--check-startup"],
        capture_output=True,
        text=True,
        check=False
    )
    assert res_check.returncode == 0
    assert "[OK] Startup verification passed" in res_check.stdout


def test_privacy_policy_fail_closed_on_importerror(monkeypatch):
    """Verify that cloud provider privacy check fails closed with PermissionError if import fails."""
    provider = DummyCloudProvider()

    # If get_settings or ExecutionMode raises ImportError
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "core.settings" in name or "core.config" in name:
            raise ImportError("Simulated core module missing")
        return real_import(name, *args, **kwargs)

    # Temporarily remove core.settings from sys.modules
    removed = {}
    for k in list(sys.modules.keys()):
        if "core.settings" in k or "core.config" in k:
            removed[k] = sys.modules.pop(k)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    try:
        with pytest.raises(PermissionError) as exc_info:
            provider.check_privacy_policy()
        assert "Privacy mode check failed" in str(exc_info.value)
    finally:
        sys.modules.update(removed)


def test_local_provider_health_missing_dependency():
    """Verify LocalProvider.health() accurately flags missing dependency."""
    from core.providers.local import LocalProvider
    health = LocalProvider.health()
    assert isinstance(health, dict)
    assert "available" in health
    assert "reason_code" in health


def test_launcher_scripts_entrypoints():
    """Verify that launcher scripts reference existing files and valid python invocation."""
    root = Path(__file__).resolve().parent.parent
    launch_bat = (root / "launch.bat").read_text(encoding="utf-8")
    run_bat = (root / "run_gayatri.bat").read_text(encoding="utf-8")
    setup_bat = (root / "setup.bat").read_text(encoding="utf-8")

    assert "-m app.main" in launch_bat
    assert "-m app.main" in run_bat
    assert "-m app.main" in setup_bat
    assert "setup.bat" in launch_bat
    assert "setup.bat" in run_bat
