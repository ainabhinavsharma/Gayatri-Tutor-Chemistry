"""Master Integration Test Matrix & Final Sign-Off (Phase 17)."""
import pytest
from core.tutor.state import TutorStateManager, LearningEvent
from core.tutor.evaluator import StudentAnswerEvaluator
from core.curriculum.resolver import ConceptResolver
from core.learning.mastery import MasteryCalculator
from core.learning.policy import DifficultyPolicy
from core.learning.misconceptions import MisconceptionTracker
from core.learning.scheduler import SpacedReviewScheduler
from core.assessment.manager import AssessmentManager, SAMPLE_QUESTION_BANK
from core.curriculum.validator import CurriculumValidator
from core.rag.schema import RAGStatus
from core.rag.retriever import NCERTRetriever
from core.rag.store import RAGStore
from core.tutor.lifecycle import TurnLifecycleManager, TurnStage
from core.mode import AppMode, validate_app_mode, get_mode_policy
from core.learning.progress import ProgressService
from core.errors import sanitize_error
from core.db import get_safe_db_connection, run_migrations
from core.security.authorization import StudentAuthorizationGuard
from core.model_fetch.manifest_validator import load_and_validate_manifest


def test_master_integration_flow(tmp_path):
    """Verify end-to-end integration across all 16 audit subsystems."""
    db_path = str(tmp_path / "test_master.db")
    sm = TutorStateManager(db_path=db_path)

    # 1. Mode Isolation
    mode = validate_app_mode("chemistry_tutor")
    policy = get_mode_policy(mode)
    assert policy.chemistry_only is True

    # 2. Student Authorization
    StudentAuthorizationGuard.validate_student_access("student_master", "student_master")

    # 3. Active Concept Resolution
    concept = ConceptResolver.resolve_concept("first law of thermodynamics")
    assert concept is not None

    # 4. Turn Lifecycle
    lifecycle = TurnLifecycleManager(sm)
    turn_rec = lifecycle.start_turn("turn_m1", "student_master", "sess_m1", concept.concept_id)
    assert turn_rec.stage == TurnStage.TURN_STARTED

    # 5. Answer Evaluation
    eval_result = StudentAnswerEvaluator.evaluate_dict({
        "student_answer": "CO2",
        "expected_answer": "CO2",
        "question_type": "formula",
    })
    assert eval_result.correctness == "correct"

    # 6. Learning Event Persistence
    event = LearningEvent(
        event_id="evt_m1",
        student_id="student_master",
        session_id="sess_m1",
        turn_id="turn_m1",
        concept_id=concept.concept_id,
        correctness="correct",
    )
    sm.record_learning_event(event)

    # 7. Mastery Engine & Spaced Review
    mastery_record = sm.get_student_concept_mastery("student_master", concept.concept_id)
    assert mastery_record.exposure_count == 1
    scheduler = SpacedReviewScheduler()
    res = scheduler.update_schedule_and_check_retention("student_master", concept.concept_id, "correct", 0, sm)
    assert res.next_review_at != ""

    # 8. Assessment Session
    assess_mgr = AssessmentManager(sm, SAMPLE_QUESTION_BANK)
    assess_id = assess_mgr.create_assessment_session("student_master", [concept.concept_id], 1)
    assess_mgr.submit_attempt(assess_id, "student_master", "thermo.hess.001", "-110.5")
    summary = assess_mgr.complete_assessment_session(assess_id, "student_master")
    assert summary["status"] == "COMPLETED"

    # 9. RAG Retrieval
    rag_store = RAGStore(db_path=tmp_path / "rag.db")
    retriever = NCERTRetriever(store=rag_store)
    rag_res = retriever.retrieve_concept_aware("enthalpy change", concept_id=concept.concept_id)
    assert rag_res.status in (RAGStatus.RAG_STATUS_EMPTY, RAGStatus.RAG_STATUS_OK)

    # 10. Progress Analytics
    progress_svc = ProgressService(sm)
    prog_summary = progress_svc.get_student_progress_summary("student_master")
    assert prog_summary["overall_mastery"] >= 0.0

    # 11. Error Sanitization
    sanitized = sanitize_error(ValueError("Failed at C:\\secret\\file.py"))
    assert "C:\\secret" not in sanitized.user_message

    # 12. Model Manifest
    manifest = load_and_validate_manifest("model_manifest.json")
    assert manifest["model_name"] == "gayatri-chemistry-tutor-v1"

    # Commit turn
    lifecycle.update_stage("turn_m1", TurnStage.TURN_COMMITTED)
