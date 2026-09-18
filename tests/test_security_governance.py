"""Tests for Phase 12 — Security, Failure Handling, and Performance."""
from __future__ import annotations

import json
import pytest

from core.mode import AppMode, InvalidAppModeError, validate_app_mode
from app.bridge import Bridge


class TestServerSideModeValidation:
    def test_valid_mode_pass(self):
        assert validate_app_mode("chemistry_tutor") == AppMode.CHEMISTRY_TUTOR
        assert validate_app_mode("general_assistant") == AppMode.GENERAL_ASSISTANT

    def test_invalid_mode_rejected(self):
        with pytest.raises(InvalidAppModeError):
            validate_app_mode("unauthorized_admin_mode")

        with pytest.raises(InvalidAppModeError):
            validate_app_mode("legacy_agent_executor")


class TestBridgeSecurityIsolation:
    def test_bridge_has_no_generic_execute_slot(self):
        bridge = Bridge()
        assert not hasattr(bridge, "execute_agent")
        assert not hasattr(bridge, "run_tool")
        assert not hasattr(bridge, "call_any_agent")

    def test_bridge_cancel_generation_idempotent(self):
        bridge = Bridge()
        # Calling cancel when no generation is active should be safe & idempotent
        bridge.cancel_generation()
        bridge.cancel_generation()
