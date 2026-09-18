"""Tests for Phase 9 — Two-Screen UI Architecture & Bridge Methods."""
from __future__ import annotations

import json
import pytest
from app.bridge import Bridge


class TestTwoScreenUIBridge:
    def test_get_sessions_by_mode_chemistry(self, qtbot):
        bridge = Bridge()
        raw = bridge.get_sessions_by_mode("chemistry_tutor")
        data = json.loads(raw)
        assert data["ok"] is True
        assert isinstance(data["sessions"], list)

    def test_get_sessions_by_mode_general(self, qtbot):
        bridge = Bridge()
        raw = bridge.get_sessions_by_mode("general_assistant")
        data = json.loads(raw)
        assert data["ok"] is True
        assert isinstance(data["sessions"], list)

    def test_legacy_get_agents_returns_ok(self, qtbot):
        bridge = Bridge()
        raw = bridge.get_agents()
        data = json.loads(raw)
        assert data["ok"] is True
