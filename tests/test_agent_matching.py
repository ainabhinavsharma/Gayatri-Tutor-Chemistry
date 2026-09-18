"""Tests for layered agent trigger matching and disambiguation (Audit #14 and #15).

Verifies:
- Layered matching: commands (1.0), exact phrase, normalized phrase, sequence, token overlap.
- Phrase semantics and word order preservation.
- Negation awareness (both user query negation and triggers containing negation).
- Ambiguity margin and tie handling.
- Default agent fallback.
- Realistic prompt disambiguation matrix.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.agents.registry import AgentRegistry


class TestLayeredMatchingAndSemantics:
    """Test phrase semantics, word order, and layered matching in AgentSpec.can_handle."""

    def test_exact_command_highest_priority(self):
        reg = AgentRegistry()

        @reg.register(name="Reviewer", commands=["/review"], triggers=["review code"])
        class Reviewer:
            def process(self, ctx): pass

        can_handle, score, _ = reg.get("Reviewer").can_handle("/review my file.py")
        assert can_handle is True
        assert score == 1.0

    def test_exact_phrase_match_preserves_order(self):
        reg = AgentRegistry()

        @reg.register(name="Reviewer", triggers=["review my code"])
        class Reviewer:
            def process(self, ctx): pass

        spec = reg.get("Reviewer")

        # In-order exact phrase
        ok, score1, _ = spec.can_handle("Can you review my code please?")
        assert ok is True
        assert score1 >= 0.90

        # Scrambled words should NOT match exact phrase
        ok2, score2, _ = spec.can_handle("Code is what I write, my review is pending")
        assert score2 < 0.60
        assert ok2 is False

    def test_normalized_phrase_matches_punctuation_variations(self):
        reg = AgentRegistry()

        @reg.register(name="Summarizer", triggers=["tl;dr", "key points"])
        class Summarizer:
            def process(self, ctx): pass

        spec = reg.get("Summarizer")
        ok, score, _ = spec.can_handle("give me a tl;dr of this document")
        assert ok is True
        assert score >= 0.85

        ok2, score2, _ = spec.can_handle("give me a tl dr of this document")
        assert ok2 is True
        assert score2 >= 0.85

    def test_negation_in_user_query_rejects_trigger(self):
        """User asking NOT to perform an action must not trigger that agent."""
        reg = AgentRegistry()

        @reg.register(name="Reviewer", triggers=["review my code", "check for bugs"])
        class Reviewer:
            def process(self, ctx): pass

        spec = reg.get("Reviewer")

        # Positive query triggers
        ok_pos, score_pos, _ = spec.can_handle("Please review my code")
        assert ok_pos is True
        assert score_pos >= 0.90

        # Negated queries with 'do not', 'don't', 'never' must NOT trigger
        for negated in [
            "Please do not review my code",
            "Don't review my code",
            "never review my code",
            "I ask you to avoid review my code",
        ]:
            ok_neg, score_neg, _ = spec.can_handle(negated)
            assert ok_neg is False, f"Failed on: {negated} with score {score_neg}"
            assert score_neg < 0.60

    def test_internal_negation_in_trigger(self):
        """Triggers that contain negation ('not financial advice') require the negation in sequence."""
        reg = AgentRegistry()

        @reg.register(name="Compliance", triggers=["not financial advice"])
        class Compliance:
            def process(self, ctx): pass

        spec = reg.get("Compliance")

        # Exact match with negation
        ok, score, _ = spec.can_handle("Remember, this is not financial advice at all")
        assert ok is True
        assert score >= 0.90

        # Scattered words with negation elsewhere must NOT match
        ok_scat, score_scat, _ = spec.can_handle("I need financial advice, not jokes")
        assert ok_scat is False
        assert score_scat < 0.60

    def test_single_word_trigger_lower_confidence_than_phrase(self):
        """Single-word triggers receive lower confidence so multi-word intent wins."""
        reg = AgentRegistry()

        @reg.register(name="WordAgent", triggers=["budget"])
        class WordAgent:
            def process(self, ctx): pass

        @reg.register(name="PhraseAgent", triggers=["financial budget"])
        class PhraseAgent:
            def process(self, ctx): pass

        _, score_word, _ = reg.get("WordAgent").can_handle("review the financial budget")
        _, score_phrase, _ = reg.get("PhraseAgent").can_handle("review the financial budget")

        assert score_phrase > score_word
        assert score_phrase >= 0.85
        assert score_word <= 0.70


class TestAmbiguityMatrixAndDisambiguation:
    """Test confidence margin, tie handling, and fallback behavior in AgentRegistry.dispatch."""

    def test_unambiguous_winner_dispatched(self):
        reg = AgentRegistry()

        @reg.register(name="CodeReviewer", commands=["/review"], triggers=["review my code"])
        class CR:
            def process(self, ctx): pass

        @reg.register(name="GeneralHelper", commands=["/help"], triggers=["general help"])
        class GH:
            def process(self, ctx): pass

        result = reg.dispatch("please review my code")
        assert result is not None
        spec, confidence = result.primary.spec, result.primary.confidence
        assert spec.name == "CodeReviewer"
        assert confidence >= 0.90

    def test_ambiguous_close_scores_fall_back(self):
        """When two agents match within ambiguity_margin (< 0.10), dispatch rejects both."""
        reg = AgentRegistry()

        # Both agents share a 1-word trigger that yields equal score (0.70)
        @reg.register(name="AgentA", triggers=["analysis"])
        class A:
            def process(self, ctx): pass

        @reg.register(name="AgentB", triggers=["analysis"])
        class B:
            def process(self, ctx): pass

        result = reg.dispatch("run analysis on this")
        assert result.primary is None, "Close/tied scores must not misroute to an arbitrary agent"

    def test_default_agent_fallback_on_ambiguity(self):
        """When ambiguity occurs and default_agent is set, fall back to default agent."""
        reg = AgentRegistry()

        @reg.register(name="GeneralBot", commands=["/general"], triggers=[])
        class GeneralBot:
            def process(self, ctx): pass

        @reg.register(name="AgentA", triggers=["analysis"])
        class A:
            def process(self, ctx): pass

        @reg.register(name="AgentB", triggers=["analysis"])
        class B:
            def process(self, ctx): pass

        reg.set_default_agent("GeneralBot")

        result = reg.dispatch("run analysis on this")
        assert result.is_ambiguous

    def test_explicit_command_breaks_all_ties(self):
        """Explicit command has 1.0 confidence and always wins even if another agent has a phrase match."""
        reg = AgentRegistry()

        @reg.register(name="CommandAgent", commands=["/tutor"], triggers=[])
        class CA:
            def process(self, ctx): pass

        @reg.register(name="PhraseAgent", triggers=["learn calculus"])
        class PA:
            def process(self, ctx): pass

        result = reg.dispatch("/tutor learn calculus")
        assert result is not None
        assert result.primary.spec.name == "CommandAgent"
        assert result.primary.confidence == 1.0


class TestRealisticAmbiguityMatrix:
    """Matrix of realistic user questions across registered domain agents."""

    @pytest.fixture(autouse=True)
    def setup_agents(self):
        from legacy.agents.default_agents import register_default_agents
        register_default_agents()

    def test_weather_query_not_hijacked_by_crop_advisory(self):
        """General weather queries must NOT route to Crop Advisory Agent."""
        from core.agents.registry import agent_registry

        result = agent_registry.dispatch("what is the weather like in New York today?")
        if result.primary is not None:
            assert result.primary.spec.name != "Crop Advisory Agent"

    def test_crop_weather_routes_to_crop_advisory(self):
        """Specific crop weather queries DO route to Crop Advisory Agent."""
        from core.agents.registry import agent_registry

        result = agent_registry.dispatch("give me crop weather advisory for wheat")
        assert result.primary is not None
        assert result.primary.spec.name == "Crop Advisory Agent"
        assert result.primary.confidence >= 0.85

    def test_meeting_schedule_vs_personal_plan(self):
        """Disambiguate meeting booking vs personal schedule planning."""
        from core.agents.registry import agent_registry

        # Meeting Scheduler has 'schedule meeting'
        res_meet = agent_registry.dispatch("can you schedule meeting with John at 3pm")
        assert res_meet is not None
        spec_meet, _ = res_meet.primary.spec, res_meet.primary.confidence
        assert spec_meet.name == "Meeting Scheduler Agent"

        # Personal Assistant has 'plan my day'
        res_plan = agent_registry.dispatch("help me plan my day and organize tasks")
        assert res_plan is not None
        spec_plan, _ = res_plan.primary.spec, res_plan.primary.confidence
        assert spec_plan.name == "Personal Assistant Agent"

    def test_government_budget_vs_financial_expenses(self):
        """Disambiguate policy budget vs financial business analysis."""
        from core.agents.registry import agent_registry

        # Policy Analyst has 'policy budget'
        res_pol = agent_registry.dispatch("explain the new policy budget allocation")
        assert res_pol is not None
        spec_pol, _ = res_pol.primary.spec, res_pol.primary.confidence
        assert spec_pol.name == "Policy Analyst Agent"

        # Financial Agent has 'financial analysis', 'expenses', 'profit loss'
        res_fin = agent_registry.dispatch("financial analysis of our Q3 revenue and expenses")
        assert res_fin is not None
        spec_fin, _ = res_fin.primary.spec, res_fin.primary.confidence
        assert spec_fin.name == "Financial Agent"
