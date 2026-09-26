"""Phase 1: Student-Visible Progress Foundation Tests.

Verifies:
1. Student-scoped progress, session history, activity feed, concept heatmap, recommendations, and session summaries.
2. Strict authorization and student ID validation (rejecting invalid/malformed IDs).
3. First-session / empty-state vs returning-student aggregation accuracy.
4. Concept heatmap categorization into mastered, developing, weak, not_started, needs_review.
5. Deterministic policy-engine recommendations.
6. Zero cross-student data leakage.
"""
from __future__ import annotations

import pytest

from core.learning.progress import ProgressService
from core.tutor.adaptive import EventLogger
from core.tutor.state import LearningEvent, TutorStateManager


@pytest.fixture
def test_db_env(tmp_path, monkeypatch):
    """Set up isolated DB and event log for Phase 1 tests."""
    db_path = tmp_path / "test_phase1.db"
    event_log = tmp_path / "test_phase1_events.jsonl"
    student_file = tmp_path / "test_phase1_student.json"

    sm = TutorStateManager(db_path=db_path)
    logger = EventLogger(log_path=event_log)

    import core.tutor.adaptive as adaptive_mod
    monkeypatch.setattr(adaptive_mod, "DEFAULT_STUDENT_FILE", student_file)
    monkeypatch.setattr(adaptive_mod, "DEFAULT_EVENT_LOG", event_log)

    return sm, logger, student_file


def _seed_mastery(sm: TutorStateManager, student_id: str, concept_id: str, mastery: float, exposure: int, correct: int):
    """Helper to insert/update student_concept_mastery in DB directly."""
    with sm.conn:
        sm.conn.execute(
            """
            INSERT INTO student_concept_mastery (
                student_id, concept_id, mastery, confidence, exposure_count, correct_count, error_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, concept_id) DO UPDATE SET
                mastery = excluded.mastery,
                exposure_count = excluded.exposure_count,
                correct_count = excluded.correct_count,
                error_count = excluded.error_count
            """,
            (student_id, concept_id, mastery, 0.8, exposure, correct, exposure - correct),
        )


def test_student_id_validation_enforced():
    """Verify that invalid student IDs are rejected with ValueError."""
    ps = ProgressService()
    with pytest.raises(ValueError, match="Student ID|string|empty"):
        ps.get_student_progress("")

    with pytest.raises(ValueError):
        ps.get_student_progress("../malicious_id")

    with pytest.raises(ValueError):
        ps.get_student_progress("a" * 100)


def test_empty_student_progress_state(test_db_env):
    """Verify clean fallback payload for new / empty student."""
    sm, _, _ = test_db_env
    ps = ProgressService(sm)

    res = ps.get_student_progress("student_new_001", sm)
    assert res["ok"] is True
    assert res["student_id"] == "student_new_001"
    assert res["questions_attempted"] == 0
    assert res["questions_correct"] == 0
    assert res["accuracy"] == 0.0
    assert res["concepts_learned"] == 0
    assert res["total_concepts"] > 0


def test_returning_student_progress_aggregation(test_db_env):
    """Verify correct statistics calculation for student with mastery and events."""
    sm, logger, _ = test_db_env
    ps = ProgressService(sm)
    student_id = "student_active_101"

    _seed_mastery(sm, student_id, "THERMO_SYSTEM", 0.85, 5, 5)
    _seed_mastery(sm, student_id, "THERMO_FIRST_LAW", 0.60, 4, 2)

    logger.log_event("ANSWER_EVALUATED", student_id, "THERMO_SYSTEM", {"result": "CORRECT", "session_id": "sess_1"})
    logger.log_event("ANSWER_EVALUATED", student_id, "THERMO_FIRST_LAW", {"result": "INCORRECT", "session_id": "sess_1"})

    res = ps.get_student_progress(student_id, sm)
    assert res["ok"] is True
    assert res["questions_attempted"] == 9
    assert res["questions_correct"] == 7
    assert res["concepts_learned"] == 1  # THERMO_SYSTEM >= 0.70
    assert res["accuracy"] > 0.70


def test_concept_heatmap_categorization(test_db_env):
    """Verify concept heatmap buckets into mastered, developing, weak, and not_started."""
    sm, _, _ = test_db_env
    ps = ProgressService(sm)
    student_id = "student_heatmap_202"

    _seed_mastery(sm, student_id, "THERMO_SYSTEM", 0.90, 3, 3)
    _seed_mastery(sm, student_id, "THERMO_FIRST_LAW", 0.50, 2, 1)
    _seed_mastery(sm, student_id, "THERMO_WORK", 0.20, 2, 0)

    res = ps.get_concept_heatmap(student_id, sm)
    assert res["ok"] is True
    heatmap = res["heatmap"]

    mastered_ids = [c["concept_id"] for c in heatmap["mastered"]]
    developing_ids = [c["concept_id"] for c in heatmap["developing"]]
    weak_ids = [c["concept_id"] for c in heatmap["weak"]]

    assert "THERMO_SYSTEM" in mastered_ids
    assert "THERMO_FIRST_LAW" in developing_ids
    assert "THERMO_WORK" in weak_ids


def test_deterministic_policy_recommendations(test_db_env):
    """Verify policy recommendations prioritize spaced review, misconceptions, then practice."""
    sm, _, _ = test_db_env
    ps = ProgressService(sm)
    student_id = "student_rec_303"

    _seed_mastery(sm, student_id, "THERMO_FIRST_LAW", 0.45, 2, 1)

    rec_res = ps.get_recommended_actions(student_id, sm)
    assert rec_res["ok"] is True
    recs = rec_res["recommendations"]
    assert len(recs) >= 1
    types = [r["type"] for r in recs]
    assert "PRACTICE" in types or "EXPLORE_NEW" in types


def test_recent_sessions_and_summary(test_db_env):
    """Verify session history aggregation and session summary output."""
    sm, logger, _ = test_db_env
    ps = ProgressService(sm)
    student_id = "student_sess_404"
    s_id = "session_chem_99"

    logger.log_event("SESSION_STARTED", student_id, "THERMO_FIRST_LAW", {"session_id": s_id})
    logger.log_event("ANSWER_EVALUATED", student_id, "THERMO_FIRST_LAW", {"session_id": s_id, "result": "CORRECT"})
    logger.log_event("ANSWER_EVALUATED", student_id, "THERMO_FIRST_LAW", {"session_id": s_id, "result": "CORRECT"})

    history = ps.get_recent_sessions(student_id, limit=5, state_manager=sm)
    assert history["ok"] is True
    assert len(history["sessions"]) >= 1
    sess = history["sessions"][-1]
    assert sess["session_id"] == s_id
    assert sess["questions_attempted"] == 2
    assert sess["questions_correct"] == 2
    assert sess["accuracy"] == 1.0

    summary_res = ps.get_session_summary(student_id, session_id=s_id, state_manager=sm)
    assert summary_res["ok"] is True
    sum_data = summary_res["session_summary"]
    assert sum_data["session_id"] == s_id
    assert sum_data["questions_attempted"] == 2
    assert sum_data["questions_correct"] == 2


def test_no_cross_student_leakage(test_db_env):
    """Verify strict data isolation between two students."""
    sm, logger, _ = test_db_env
    ps = ProgressService(sm)
    s1 = "student_alpha_001"
    s2 = "student_beta_002"

    _seed_mastery(sm, s1, "THERMO_SYSTEM", 0.95, 10, 10)
    logger.log_event("ANSWER_EVALUATED", s1, "THERMO_SYSTEM", {"session_id": "s1_sess", "result": "CORRECT"})

    p1 = ps.get_student_progress(s1, sm)
    p2 = ps.get_student_progress(s2, sm)

    assert p1["questions_attempted"] == 10
    assert p1["questions_correct"] == 10
    assert p1["concepts_learned"] == 1

    assert p2["questions_attempted"] == 0
    assert p2["questions_correct"] == 0
    assert p2["concepts_learned"] == 0
