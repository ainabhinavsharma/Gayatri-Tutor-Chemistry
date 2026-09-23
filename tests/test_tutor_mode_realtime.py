"""Tests for real-time pedagogical mode switching and synchronization."""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.bridge.facade import Bridge
from core.tutor.adaptive import StudentProfile, EventLogger
from core.runtimes.chemistry import ChemistryTutorRuntime


def test_bridge_set_tutor_mode_valid():
    """Test switching tutor modes via bridge slot."""
    bridge = Bridge()
    for mode in ["EXPLAIN", "QUESTION", "HINT", "EVALUATE", "REMEDIATE", "SUMMARY"]:
        raw = bridge.set_tutor_mode(mode)
        res = json.loads(raw)
        assert res["ok"] is True
        assert res["mode"] == mode

        student = StudentProfile.load_from_file()
        assert student.current_mode == mode


def test_bridge_set_tutor_mode_invalid():
    """Test invalid tutor mode is rejected."""
    bridge = Bridge()
    raw = bridge.set_tutor_mode("INVALID_MODE")
    res = json.loads(raw)
    assert res["ok"] is False
    assert "Invalid mode" in res["error"]


def test_bridge_telemetry_reflects_mode():
    """Test get_demo_telemetry reflects tutor mode changes."""
    bridge = Bridge()
    bridge.set_tutor_mode("QUESTION")
    telemetry = json.loads(bridge.get_demo_telemetry())
    assert telemetry["mode"] == "QUESTION"
    assert telemetry["next_action"] == "EVALUATE"

    bridge.set_tutor_mode("HINT")
    telemetry = json.loads(bridge.get_demo_telemetry())
    assert telemetry["mode"] == "HINT"
    assert "HINT LVL" in telemetry["next_action"]

    bridge.set_tutor_mode("REMEDIATE")
    telemetry = json.loads(bridge.get_demo_telemetry())
    assert telemetry["mode"] == "REMEDIATE"
    assert telemetry["concept_id"] == "THERMO_INTERNAL_ENERGY"


def test_chemistry_runtime_mode_transitions(monkeypatch):
    """Test dynamic mode transitions in ChemistryTutorRuntime.stream."""
    runtime = ChemistryTutorRuntime()

    # Mock inference service to return a dummy generator without loading heavy model
    mock_service = MagicMock()
    mock_service.stream_chat.return_value = iter(["Sample", " response"])
    monkeypatch.setattr("core.runtimes.chemistry.get_inference_service", lambda: mock_service)

    # 1. Ask for explanation -> EXPLAIN mode
    list(runtime.stream("Please explain the First Law of Thermodynamics.", context=None))
    student = StudentProfile.load_from_file()
    assert student.current_mode == "EXPLAIN"

    # 2. Ask for practice problem -> QUESTION mode
    list(runtime.stream("Give me a practice problem on this.", context=None))
    student = StudentProfile.load_from_file()
    assert student.current_mode == "QUESTION"

    # 3. Submit wrong answer with sign error -> EVALUATE mode with misconception
    list(runtime.stream("delta U is 700 J because we add them up: 500 + 200 = 700 J.", context=None))
    student = StudentProfile.load_from_file()
    assert student.current_mode == "EVALUATE"
    assert "THERMO_SIGN_CONVENTION" in student.misconceptions

    # 4. Ask for a hint -> HINT mode
    list(runtime.stream("I am confused, can you give me a hint?", context=None))
    student = StudentProfile.load_from_file()
    assert student.current_mode == "HINT"
    assert student.active_hint_level >= 1

    # 5. Struggle with prerequisite -> REMEDIATE mode
    list(runtime.stream("I don't really understand what internal energy actually represents.", context=None))
    student = StudentProfile.load_from_file()
    assert student.current_mode == "REMEDIATE"
    assert student.current_concept == "THERMO_INTERNAL_ENERGY"
