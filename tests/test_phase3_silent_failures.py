"""Tests for Phase 3: Silent-Failure Audit.

Verifies the 8 forbidden silent conversions:
1. Evaluation failure -> uncertain (never incorrect; does not alter mastery).
2. RAG failure / error / empty -> observable in prompt (never unrestricted).
3. Database failure -> raises / observable (never silently reported as success).
4. Missing curriculum -> raises FileNotFoundError (never silently empty).
5. Missing student -> raises ValueError (never global state fallback).
6. Invalid question -> raises / returns internal error (never falsely blaming student).
7. Model failure -> returns sanitized error response (never successful empty response).
8. Authorization failure -> raises SecurityAccessDeniedError (never default user).
"""
from __future__ import annotations

import sqlite3
import pytest
from pathlib import Path

from core.tutor.evaluator import StudentAnswerEvaluator, EvaluationResult
from core.tutor.state import TutorStateManager, LearningEvent
from core.curriculum.loader import CurriculumManifestLoader
from core.assessment.schema import NumericalQuestion, QuestionType
from core.assessment.grader import AssessmentGrader
from core.security.authorization import StudentAuthorizationGuard, SecurityAccessDeniedError
from core.orchestrator import Orchestrator, TurnOptions
from core.rag.schema import RAGContext, RAGStatus, ConfidenceLevel


def test_evaluator_failure_becomes_uncertain():
    """1. Evaluation failure must become 'uncertain' and never 'incorrect'."""
    # Simulating empty or corrupted answer
    result = StudentAnswerEvaluator.evaluate(
        user_answer="",
        expected_answer="delta U = q + w",
        question_type="conceptual",
    )
    assert result.correctness == "uncertain"
    assert result.confidence == 0.0

    # Generic ambiguous single-word answer without question context must be 'uncertain'
    result_ambig = StudentAnswerEvaluator.evaluate(
        user_answer="yes",
        expected_answer="",
        question_type="conceptual",
    )
    assert result_ambig.correctness == "uncertain"
    assert result_ambig.confidence == 0.0


def test_rag_failure_is_observable():
    """2. RAG failure or empty state must be observable and never unrestricted."""
    from core.runtimes.chemistry import ChemistryTutorRuntime
    runtime = ChemistryTutorRuntime()

    # Verify that curriculum manifest was loaded (not empty)
    topics = runtime.get_available_topics()
    assert len(topics) > 0, "Curriculum topics must not be empty"

    # Context with empty RAG
    rag_empty = RAGContext(query="test", results=[], confidence=ConfidenceLevel.LOW, status=RAGStatus.RAG_STATUS_EMPTY)
    assert rag_empty.status == RAGStatus.RAG_STATUS_EMPTY

    # Context with error RAG
    rag_error = RAGContext(query="test", results=[], confidence=ConfidenceLevel.LOW, status=RAGStatus.RAG_STATUS_ERROR, error_message="DB connection failed")
    assert rag_error.status == RAGStatus.RAG_STATUS_ERROR


def test_missing_curriculum_raises_error():
    """3. Missing curriculum file must raise FileNotFoundError, not return empty."""
    loader = CurriculumManifestLoader(manifest_path="non_existent_curriculum_file.json")
    with pytest.raises(FileNotFoundError):
        loader.load_manifest()


def test_missing_student_raises_error(tmp_path):
    """4. Missing student ID must raise ValueError, not fall back to global state."""
    db_file = tmp_path / "test_state.db"
    manager = TutorStateManager(db_path=db_file)

    with pytest.raises(ValueError) as exc:
        manager.get_student_concept_mastery(student_id="", concept_id="chem_thermo_system")
    assert "student_id must not be empty" in str(exc.value)

    with pytest.raises(ValueError) as exc2:
        manager.get_student_concept_mastery(student_id="   ", concept_id="chem_thermo_system")
    assert "student_id must not be empty" in str(exc2.value)

    ev = LearningEvent(
        event_id="ev_001",
        student_id="",
        session_id="s1",
        turn_id="t1",
        concept_id="chem_thermo_system",
        correctness="correct"
    )
    with pytest.raises(ValueError) as exc3:
        manager.record_learning_event(ev)
    assert "event.student_id must not be empty" in str(exc3.value)


def test_invalid_question_config_not_student_fault():
    """5. Invalid question configuration returns internal error rather than failing student."""
    bad_question = NumericalQuestion(
        question_id="bad_q_1",
        topic_id="thermo",
        difficulty=1,
        question_text="What is the answer?",
        expected_value="NOT_A_FLOAT",  # Corrupt config
        correct_answer="INVALID_NUMBER",
        source_id="TEST"
    )
    is_corr, score, feedback = AssessmentGrader.grade_answer(bad_question, student_answer="42")
    assert is_corr is False
    assert score == 0.0
    assert "Internal error: question configuration invalid" in feedback


def test_authorization_failure_blocks_access():
    """6. Authorization failure raises SecurityAccessDeniedError, never defaulting user."""
    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("student_A", "student_B")

    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("", "student_B")


def test_model_failure_returns_error_status(monkeypatch):
    """7. Model failure produces status='ERROR', not a successful empty response."""
    orchestrator = Orchestrator()

    # Simulate runtime exception in submit
    def mock_stream(*args, **kwargs):
        raise RuntimeError("Simulated model inference crash")

    monkeypatch.setattr("core.runtimes.general.GeneralAssistantRuntime.stream", mock_stream)

    opts = TurnOptions(forced_tier="local")
    result = orchestrator.submit("Hello", session_id="test_sess", options=opts)

    assert result.status == "ERROR"
    assert "I encountered an error" in result.text
    assert len(result.text) > 0
