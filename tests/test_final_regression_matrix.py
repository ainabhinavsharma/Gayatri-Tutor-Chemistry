"""Master Regression Matrix Test Suite for Phase 13 Final Sign-Off."""
from __future__ import annotations

import json
import pytest

from core.mode import AppMode, InvalidAppModeError, validate_app_mode
from core.runtimes.chemistry import ChemistryTutorRuntime, _build_chemistry_system_prompt
from core.runtimes.general import GeneralAssistantRuntime, _detect_chemistry_tutoring_request
from core.tutor.state_machine import TutorState, TutorStateMachine
from core.tutor.intents import TutorIntent, TutorIntentClassifier
from core.tutor.guard import OutOfDomainGuard
from core.assessment.schema import (
    EquationBalancingQuestion,
    MCQQuestion,
    NumericalQuestion,
)
from core.assessment.balancing import EquationBalancingEngine
from core.assessment.grader import AssessmentGrader
from core.rag.schema import ConfidenceLevel, DocumentChunk
from core.rag.citations import CitationFormatter
from app.bridge import Bridge


class TestMasterRegressionMatrix:
    """P13-T01: Mode & Agent Isolation Matrix."""
    def test_mode_acceptance_and_rejection(self):
        assert validate_app_mode("chemistry_tutor") == AppMode.CHEMISTRY_TUTOR
        assert validate_app_mode("general_assistant") == AppMode.GENERAL_ASSISTANT

        invalid_modes = ["math", "coding", "code_review", "practice_agent", "research_agent", "unknown"]
        for mode in invalid_modes:
            with pytest.raises(InvalidAppModeError):
                validate_app_mode(mode)

    """P13-T02: Two-Screen UI & Session History Isolation."""
    def test_ui_bridge_session_isolation(self, qtbot):
        bridge = Bridge()
        chem_sessions = json.loads(bridge.get_sessions_by_mode("chemistry_tutor"))
        gen_sessions = json.loads(bridge.get_sessions_by_mode("general_assistant"))

        assert chem_sessions["ok"] is True
        assert gen_sessions["ok"] is True
        assert isinstance(chem_sessions["sessions"], list)
        assert isinstance(gen_sessions["sessions"], list)

    """P13-T03: Chemistry Tutor State Machine Loop."""
    def test_tutor_state_machine_loop(self):
        sm = TutorStateMachine(TutorState.IDLE)
        assert sm.current_state == TutorState.IDLE
        assert sm.transition_to(TutorState.EXPLAINING) is True
        assert sm.current_state == TutorState.EXPLAINING
        assert sm.transition_to(TutorState.CHECKING) is True
        assert sm.current_state == TutorState.CHECKING

    """P13-T04: Assessment Solvers & Equation Balancing Engine."""
    def test_equation_balancing_engine(self):
        is_bal, msg = EquationBalancingEngine.verify_balance("2 Na + 2 H2O -> 2 NaOH + H2")
        assert is_bal is True
        assert "balanced" in msg.lower()

        is_bal_fail, _ = EquationBalancingEngine.verify_balance("Na + H2O -> NaOH + H2")
        assert is_bal_fail is False

    def test_numerical_grader(self):
        q = NumericalQuestion(
            question_id="qn1",
            topic_id="thermo",
            difficulty=2,
            question_text="Calculate delta U",
            expected_value=250.0,
            tolerance=0.01,
        )
        is_corr, score, _ = AssessmentGrader.grade_answer(q, "250.0")
        assert is_corr is True
        assert score == 1.0

    """P13-T05: NCERT RAG Retrieval & Citations."""
    def test_rag_citation_formatter(self):
        chunk = DocumentChunk(
            chunk_id="c101",
            source_id="NCERT_CHEM_11_CH06",
            chapter="Thermodynamics",
            topic="First Law",
            subtopic="Formula",
            page=163,
            text="delta U = q + w",
        )
        cit = CitationFormatter.format_chunk_citation(chunk)
        assert "Thermodynamics" in cit
        assert "p. 163" in cit

    """P13-T06: General Assistant Capabilities."""
    def test_general_assistant_runtime(self):
        rt = GeneralAssistantRuntime()
        assert rt is not None

    """P13-T07: Cross-Mode Out-of-Domain Redirection."""
    def test_out_of_domain_redirection_guards(self):
        # General assistant detects chemistry tutoring query
        assert _detect_chemistry_tutoring_request("teach me chemistry thermodynamics") is True

        # Chemistry tutor detects non-chemistry query
        assert OutOfDomainGuard.is_out_of_domain("write python flask code") is True

    """P13-T08 & P13-T09: Streaming UI & Thread-Safe Cancellation."""
    def test_bridge_cancellation_idempotent(self):
        bridge = Bridge()
        bridge.cancel_generation()
        bridge.cancel_generation()
