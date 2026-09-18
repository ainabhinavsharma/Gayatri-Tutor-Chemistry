"""Tests for Phase 6 — Chemistry Tutor Engine."""
from __future__ import annotations

import pytest

from core.tutor.state_machine import TutorState, TutorStateMachine
from core.tutor.intents import TutorIntent, TutorIntentClassifier
from core.tutor.guard import OutOfDomainGuard
from core.tutor.adapter import StudentAdapter
from core.tutor.memory import TutorMemoryManager
from core.tutor.policies.explanation import ExplanationPolicy
from core.tutor.policies.numerical import NumericalPolicy
from core.tutor.policies.reaction import ReactionPolicy
from core.tutor.evaluator import StudentAnswerEvaluator
from core.tutor.difficulty import DifficultyManager
from core.runtimes.chemistry import ChemistryTutorRuntime


class TestTutorStateMachine:
    def test_initial_state(self):
        sm = TutorStateMachine()
        assert sm.current_state == TutorState.IDLE

    def test_valid_transition(self):
        sm = TutorStateMachine()
        assert sm.transition_to(TutorState.DISCOVERING) is True
        assert sm.current_state == TutorState.DISCOVERING

    def test_invalid_transition_fallback(self):
        sm = TutorStateMachine(TutorState.COMPLETED)
        # Invalid jump from COMPLETED -> REMEDIATING
        assert sm.transition_to(TutorState.REMEDIATING) is False
        assert sm.current_state == TutorState.EXPLAINING  # Fallback state


class TestIntentClassifier:
    def test_intent_classification(self):
        assert TutorIntentClassifier.classify("Calculate the value of delta U") == TutorIntent.SOLVE
        assert TutorIntentClassifier.classify("Give me some practice problems") == TutorIntent.PRACTICE
        assert TutorIntentClassifier.classify("Summarize Gibbs Free Energy") == TutorIntent.SUMMARIZE
        assert TutorIntentClassifier.classify("What is Heat Capacity?") == TutorIntent.EXPLAIN

    def test_empty_message_unknown_intent(self):
        assert TutorIntentClassifier.classify("") == TutorIntent.UNKNOWN


class TestOutOfDomainGuard:
    def test_out_of_domain_detection(self):
        assert OutOfDomainGuard.is_out_of_domain("write python code for a flask app") is True
        assert OutOfDomainGuard.is_out_of_domain("who won the movie award?") is True
        assert OutOfDomainGuard.is_out_of_domain("What is the first law of thermodynamics?") is False

    def test_redirection_prompt(self):
        prompt = OutOfDomainGuard.get_redirection_prompt("python code")
        assert "non-chemistry" in prompt.lower()


class TestPedagogicalPolicies:
    def test_explanation_policy(self):
        d = ExplanationPolicy.get_directive("Thermodynamics", "System", "high")
        assert "Direct Explanation" in d
        assert "Thermodynamics" in d

    def test_numerical_policy(self):
        d = NumericalPolicy.get_directive()
        assert "Given:" in d
        assert "Formula" in d
        assert "Unit Check:" in d

    def test_reaction_policy(self):
        d = ReactionPolicy.get_directive()
        assert "Reactants & Products:" in d
        assert "Equation Balancing:" in d


class TestStudentAdapterAndEvaluator:
    def test_evaluator_correct(self):
        res = StudentAnswerEvaluator.evaluate("Yes, the answer is equal to 400 J")
        assert res.correctness == "correct"
        assert res.confidence >= 0.7

    def test_evaluator_incorrect(self):
        res = StudentAnswerEvaluator.evaluate("I have no idea about this")
        assert res.correctness == "incorrect"

    def test_difficulty_adaptation(self):
        res_correct = StudentAnswerEvaluator.evaluate("Correct 400 J")
        next_diff = DifficultyManager.calculate_next_difficulty(2, res_correct)
        assert next_diff == 3

        res_incorrect = StudentAnswerEvaluator.evaluate("Wrong answer")
        next_diff_lower = DifficultyManager.calculate_next_difficulty(2, res_incorrect)
        assert next_diff_lower == 1

    def test_adapter_strategy(self):
        strat = StudentAdapter.adapt(mastery_score=0.9)
        assert strat.target_difficulty == 4
        assert strat.scaffolding_amount == "minimal"


class TestTutorMemoryManager:
    def test_memory_summary_formatting(self):
        mem = TutorMemoryManager.build_memory("Thermodynamics", "Enthalpy", 0.85, ["Sign error"], 3)
        summary = mem.formatted_summary()
        assert "Thermodynamics" in summary
        assert "85%" in summary
        assert "Sign error" in summary


class TestChemistryTutorRuntimeEngine:
    def test_runtime_state_machine_initialized(self):
        rt = ChemistryTutorRuntime()
        assert rt.state_machine.current_state == TutorState.IDLE
        assert len(rt.get_available_topics()) > 0
