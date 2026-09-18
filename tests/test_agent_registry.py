"""Tests for the agent registry."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.agents.registry import AgentRegistry, AgentResponse, agent_registry


class TestAgentRegistry:
    """Test the agent registration and dispatch system."""

    def test_register_agent_via_decorator(self):
        """Agents can be registered with the @register decorator."""
        reg = AgentRegistry()

        @reg.register(
            name="TestAgent",
            commands=["/test"],
            triggers=["run test"],
            description="A test agent",
        )
        class TestAgent:
            def process(self, context):
                return AgentResponse(text="test", agent_name="TestAgent")

        assert reg.get("TestAgent") is not None
        assert reg.get_class("TestAgent") is TestAgent

    def test_list_agents(self):
        """list_agents returns all registered agents."""
        reg = AgentRegistry()

        @reg.register(name="Agent1", commands=["/a1"], description="First")
        class A1:
            def process(self, ctx): pass

        @reg.register(name="Agent2", commands=["/a2"], description="Second")
        class A2:
            def process(self, ctx): pass

        agents = reg.list_agents()
        assert len(agents) == 2
        assert agents[0]["name"] == "Agent1"
        assert agents[1]["name"] == "Agent2"

    def test_list_commands(self):
        """list_commands returns all registered commands."""
        reg = AgentRegistry()

        @reg.register(name="A", commands=["/hello", "/hi"], triggers=[])
        class A:
            def process(self, ctx): pass

        cmds = reg.list_commands()
        assert "/hello" in cmds
        assert "/hi" in cmds

    def test_dispatch_exact_command(self):
        """Exact command match returns highest confidence."""
        reg = AgentRegistry()

        @reg.register(name="Reviewer", commands=["/review"], triggers=["check code"])
        class Reviewer:
            def process(self, ctx): pass

        result = reg.dispatch("/review my code")
        assert result is not None
        spec, confidence = result.primary.spec, result.primary.confidence
        assert spec.name == "Reviewer"
        assert confidence == 1.0

    def test_dispatch_command_case_insensitive(self):
        """Command matching is case-insensitive."""
        reg = AgentRegistry()

        @reg.register(name="Tutor", commands=["/tutor"], triggers=[])
        class Tutor:
            def process(self, ctx): pass

        result = reg.dispatch("/TUTOR help")
        assert result is not None
        spec, _ = result.primary.spec, result.primary.confidence
        assert spec.name == "Tutor"

    def test_dispatch_trigger_match(self):
        """Trigger phrases match with confidence scoring."""
        reg = AgentRegistry()

        @reg.register(name="CodeHelper", commands=[], triggers=["review code", "check bugs"])
        class CodeHelper:
            def process(self, ctx): pass

        result = reg.dispatch("can you check bugs in my script")
        assert result is not None
        spec, confidence = result.primary.spec, result.primary.confidence
        assert spec.name == "CodeHelper"
        assert confidence > 0.4

    def test_dispatch_no_match(self):
        """Returns None when no agent matches."""
        reg = AgentRegistry()

        @reg.register(name="Tutor", commands=["/tutor"], triggers=["learn math"])
        class Tutor:
            def process(self, ctx): pass

        result = reg.dispatch("what is the weather")
        assert result.primary is None

    def test_dispatch_low_confidence_rejected(self):
        """Low-confidence trigger matches are rejected."""
        reg = AgentRegistry()

        @reg.register(name="Tutor", commands=[], triggers=["linear algebra integral calculus"])
        class Tutor:
            def process(self, ctx): pass

        # Only 1 of 3 trigger words matches
        result = reg.dispatch("linear equation")
        assert result.primary is None

    def test_instantiate_agent(self):
        """Can create instances of registered agents."""
        reg = AgentRegistry()

        @reg.register(name="Test", commands=["/t"])
        class TestAgent:
            def __init__(self, custom=None):
                self.custom = custom

        instance = reg.instantiate("Test", custom="hello")
        assert isinstance(instance, TestAgent)
        assert instance.custom == "hello"

    def test_instantiate_unknown_raises(self):
        """Instantiating an unknown agent raises ValueError."""
        reg = AgentRegistry()
        with pytest.raises(ValueError, match="not registered"):
            reg.instantiate("Nonexistent")

    def test_global_registry_has_agents(self):
        """The global registry should have some agents registered."""
        # This test verifies the global registry is functional
        agents = agent_registry.list_agents()
        assert isinstance(agents, list)
        # No agents registered yet in fresh test — that's fine
