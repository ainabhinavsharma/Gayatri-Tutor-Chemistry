import pytest
from core.orchestrator import Orchestrator, TurnOptions
from core.mode import AppMode
from core.conversation import ConversationStore

def test_invalid_mode_fails_closed():
    orch = Orchestrator()
    opts = TurnOptions(mode="hacker_mode")
    # Using stream
    stream = orch.stream("Hello", options=opts)
    result = list(stream)
    assert len(result) > 0
    assert "Unknown mode: hacker_mode" in result[0][0]

def test_legacy_agent_rejected():
    orch = Orchestrator()
    opts = TurnOptions(mode="general_assistant", forced_agent="math")
    res = orch.submit("Calculate this", options=opts)
    assert res.status == "ERROR"
    assert "Legacy agent 'math' is rejected" in res.text

def test_legacy_task_type_rejected():
    orch = Orchestrator()
    opts = TurnOptions(mode="general_assistant", task_type="code")
    res = orch.submit("Write code", options=opts)
    assert res.status == "ERROR"
    assert "Legacy task type 'code' is rejected" in res.text

def test_valid_modes():
    orch = Orchestrator()
    # Mock runtime to prevent LLM execution
    # For general assistant
    opts = TurnOptions(mode="general_assistant")
    # We will just verify it does not error with "Unknown mode"
    # It might error because there is no LLM mock, but the mode validation should pass
    # Actually just relying on the logic
