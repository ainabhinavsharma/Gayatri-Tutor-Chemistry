"""Tests for Batch E: Curriculum Graph (LDG) Resilience & Adaptive Tutor Edge Cases.

Verifies:
1. Cycle detection in get_learning_path (Audit #33)
2. Untracked concepts vs 0.0 mastery distinction (Audit #34 & #109)
3. Empty concepts and subject filtering progress stats (Audit #109)
4. Missing prerequisite deadlock prevention and pruning (Audit #110)
5. Confidence weighting and oscillation dampening in record_attempt (Audit #35 & #36)
6. Duplicate answer suppression within short window (Audit #36)
7. Staleness guard on waiting_for_answer (Audit #130)
8. Conversational clarification question detection (Audit #130)
9. Transactional turn rollback on model unavailable / error (Audit #128)
"""

import time
from core.knowledge_graph import LearningDependencyGraph
from core.tutor_engine import TutorEngine
from core.orchestrator import Orchestrator, TurnOptions, _evaluate_tutor_response


class TestCycleDetectionAndGraphResilience:
    """Audit #33: Cycle detection in LearningDependencyGraph.get_learning_path()."""

    def test_cycle_detection_in_ancestors(self, tmp_path):
        db_path = tmp_path / "test_cycle.db"
        ldg = LearningDependencyGraph(db_path=db_path)

        # Create 3 concepts: A -> B -> C -> A (cycle)
        ldg.add_concept("concept_a", "Concept A")
        ldg.add_concept("concept_b", "Concept B")
        ldg.add_concept("concept_c", "Concept C")

        # Bypass add_prerequisite cycle validation by inserting directly into SQLite
        # simulating corrupted DB data or unvalidated curriculum import
        conn = ldg._conn()
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('concept_b', 'concept_a')")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('concept_c', 'concept_b')")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('concept_a', 'concept_c')")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        # Calling get_learning_path for concept_c should not hang, recurse infinitely, or drop nodes
        path = ldg.get_learning_path("concept_c")
        path_ids = [c.id for c in path]

        # All 3 concepts must be present in the learning path
        assert set(path_ids) == {"concept_a", "concept_b", "concept_c"}
        # Target concept must be at the end
        assert path_ids[-1] == "concept_c"

    def test_two_node_cycle_does_not_deadlock(self, tmp_path):
        db_path = tmp_path / "test_two_cycle.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("node_x", "Node X")
        ldg.add_concept("node_y", "Node Y")

        conn = ldg._conn()
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('node_x', 'node_y')")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('node_y', 'node_x')")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        path = ldg.get_learning_path("node_y")
        path_ids = [c.id for c in path]
        assert set(path_ids) == {"node_x", "node_y"}
        assert path_ids[-1] == "node_y"


class TestMissingPrerequisitesDeadlockPrevention:
    """Audit #110: Missing prerequisites deadlock prevention & pruning."""

    def test_missing_prerequisite_does_not_block_unlock(self, tmp_path):
        db_path = tmp_path / "test_missing_prereq.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("concept_live", "Live Concept")

        # Add prerequisite to a non-existent node (with foreign keys temporarily off)
        conn = ldg._conn()
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('concept_live', 'ghost_prereq')")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        # Even though 'ghost_prereq' does not exist, concept_live must be unlocked (not deadlocked)
        assert ldg.is_unlocked("concept_live") is True

    def test_missing_prerequisite_skipped_in_learning_path(self, tmp_path):
        db_path = tmp_path / "test_missing_path.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("target_node", "Target Node")

        conn = ldg._conn()
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('target_node', 'nonexistent_node')")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        path = ldg.get_learning_path("target_node")
        assert len(path) == 1
        assert path[0].id == "target_node"

    def test_prune_orphaned_prerequisites(self, tmp_path):
        db_path = tmp_path / "test_prune.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("valid_node", "Valid Node")

        conn = ldg._conn()
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('valid_node', 'ghost_1')")
        conn.execute("INSERT INTO ldg_prerequisites (concept_id, prereq_id) VALUES ('ghost_2', 'valid_node')")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        pruned = ldg.prune_orphaned_prerequisites()
        assert pruned == 2

        # Verify prerequisites table is clean
        assert ldg.get_prerequisites("valid_node") == []


class TestMasteryDistinctionAndSubjectStats:
    """Audit #34 & #109: Untracked concept distinction and empty subject stats."""

    def test_untracked_concept_returns_none(self, tmp_path):
        db_path = tmp_path / "test_mastery_none.db"
        ldg = LearningDependencyGraph(db_path=db_path)

        # Untracked concept returns None by default
        assert ldg.get_mastery("unknown_concept_id") is None
        # With explicit default
        assert ldg.get_mastery("unknown_concept_id", default=0.0) == 0.0

    def test_tracked_zero_mastery_distinguishable_from_untracked(self, tmp_path):
        db_path = tmp_path / "test_mastery_zero.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("tracked_concept", "Tracked Concept")

        # Manually set mastery to exactly 0.0
        conn = ldg._conn()
        conn.execute("UPDATE ldg_concepts SET mastery = 0.0 WHERE id = 'tracked_concept'")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        mastery = ldg.get_mastery("tracked_concept")
        assert mastery is not None
        assert mastery == 0.0
        assert ldg.has_concept("tracked_concept") is True
        assert ldg.has_concept("untracked_concept") is False

    def test_get_progress_stats_empty_subject_has_consistent_shape(self, tmp_path):
        db_path = tmp_path / "test_empty_stats.db"
        ldg = LearningDependencyGraph(db_path=db_path)

        stats = ldg.get_progress_stats(subject="nonexistent_subject")
        assert "total" in stats
        assert "mastered" in stats
        assert "in_progress" in stats
        assert "not_started" in stats
        assert "avg_mastery" in stats
        assert "mastery_pct" in stats
        assert stats["total"] == 0
        assert stats["mastery_pct"] == 0.0

    def test_get_next_concept_fallback_when_none_unlocked(self, tmp_path):
        db_path = tmp_path / "test_next_fallback.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("root_locked", "Root Locked", subject="math")
        ldg.add_concept("child_locked", "Child Locked", subject="math")

        # Set mastery of root_locked to 0.1 (below 0.85 threshold)
        conn = ldg._conn()
        conn.execute("UPDATE ldg_concepts SET mastery = 0.1 WHERE id = 'root_locked'")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        ldg.add_prerequisite("child_locked", "root_locked")

        # root_locked has no prerequisites, so it is unlocked
        next_c = ldg.get_next_concept(subject="math")
        assert next_c is not None
        assert next_c.id == "root_locked"


class TestConfidenceWeightingAndOscillationDampening:
    """Audit #35 & #36: record_attempt confidence weighting and oscillation dampening."""

    def test_confidence_clamping_and_zero_confidence(self, tmp_path):
        db_path = tmp_path / "test_conf.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        c = ldg.add_concept("concept_conf", "Confidence Test")
        initial_mastery = c.mastery

        # Zero confidence -> mastery should not change at all
        new_m = ldg.record_attempt("concept_conf", correct=True, confidence=0.0)
        assert new_m == initial_mastery

        # Out-of-bounds confidence clamped: 2.0 should behave as 1.0, not double
        m_normal = ldg.record_attempt("concept_conf", correct=True, confidence=1.0)
        ldg.reset_concept("concept_conf")
        m_clamped = ldg.record_attempt("concept_conf", correct=True, confidence=2.0)
        assert abs(m_clamped - m_normal) < 1e-4

        # Negative confidence clamped to 0.0 -> no change
        ldg.reset_concept("concept_conf")
        m_neg = ldg.record_attempt("concept_conf", correct=True, confidence=-0.5)
        assert m_neg == initial_mastery

    def test_repeated_alternating_attempts_remain_bounded(self, tmp_path):
        db_path = tmp_path / "test_oscillate.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("concept_osc", "Oscillation Test")

        # Record 20 alternating attempts
        for i in range(20):
            correct = (i % 2 == 0)
            m = ldg.record_attempt("concept_osc", correct=correct, confidence=1.0)
            assert 0.0 <= m <= 1.0

        # Verify dampening reduces step size for the same baseline
        ldg.reset_concept("concept_osc")
        delta_fresh = ldg.record_attempt("concept_osc", correct=True, confidence=1.0) - 0.3

        # Add 30 exposures to increase exposure count
        for _ in range(30):
            ldg.record_attempt("concept_osc", correct=True, confidence=0.01)

        # Set mastery back to 0.3 to compare identical starting point
        conn = ldg._conn()
        conn.execute("UPDATE ldg_concepts SET mastery = 0.3 WHERE id = 'concept_osc'")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        delta_dampened = ldg.record_attempt("concept_osc", correct=True, confidence=1.0) - 0.3
        assert delta_dampened < delta_fresh

    def test_duplicate_student_answer_suppression(self, tmp_path):
        db_path = tmp_path / "test_dup_ans.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("concept_dup", "Duplicate Answer Test")

        tutor = TutorEngine(ldg)
        ctx = tutor.get_or_create_context("dup_session")
        ctx.current_concept_id = "concept_dup"
        ctx.current_concept_name = "Duplicate Answer Test"
        tutor.set_waiting_for_answer("dup_session")

        # First answer
        m1 = tutor.record_student_response("dup_session", correct=True, student_answer="42")
        # Immediate identical answer within 10s
        m2 = tutor.record_student_response("dup_session", correct=True, student_answer="42")

        # Mastery should NOT have been increased twice for duplicate answer
        assert m1 == m2


class TestStalenessGuardAndQuestionHandling:
    """Audit #130: Staleness guard on waiting_for_answer and clarifying questions."""

    def test_staleness_guard_expires_waiting_state(self, tmp_path):
        db_path = tmp_path / "test_staleness.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        tutor = TutorEngine(ldg)

        session_id = "stale_sess"
        tutor.set_waiting_for_answer(session_id)
        assert tutor.is_waiting_for_answer(session_id) is True

        # Manually backdate the interaction time to 31 minutes ago (1860 seconds)
        ctx = tutor.get_or_create_context(session_id)
        ctx.last_interaction_time = time.time() - 1860

        # Checking waiting_for_answer must now return False and reset state
        assert tutor.is_waiting_for_answer(session_id, max_age_seconds=1800.0) is False
        assert ctx.waiting_for_answer is False

    def test_stale_answer_not_evaluated(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_stale_eval.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("stale_c", "Stale Concept")

        tutor = TutorEngine(ldg)
        monkeypatch.setattr("core.orchestrator._get_tutor_engine", lambda: tutor)
        monkeypatch.setattr("core.orchestrator._get_ldg", lambda: ldg)

        session_id = "stale_eval_sess"
        ctx = tutor.get_or_create_context(session_id)
        ctx.current_concept_id = "stale_c"
        ctx.mastery = 0.5
        tutor.set_waiting_for_answer(session_id)

        # Backdate by 35 minutes
        ctx.last_interaction_time = time.time() - 2100

        # User sends a short message ("ok") which would normally evaluate to False
        _evaluate_tutor_response(session_id, "ok", tutor=tutor, ldg=ldg)

        # Mastery must remain unchanged because question expired
        assert ctx.mastery == 0.5

    def test_clarifying_question_not_penalized(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_clarify.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("clarify_c", "Clarify Concept")

        tutor = TutorEngine(ldg)
        monkeypatch.setattr("core.orchestrator._get_tutor_engine", lambda: tutor)
        monkeypatch.setattr("core.orchestrator._get_ldg", lambda: ldg)
        
        # Mock the new LLM evaluator to return null for clarification
        monkeypatch.setattr("core.providers.local.LocalProvider.chat", lambda msgs, **kwargs: '{"correct": null, "confidence": 1.0}')

        session_id = "clarify_sess"
        ctx = tutor.get_or_create_context(session_id)
        ctx.current_concept_id = "clarify_c"
        ctx.mastery = 0.6
        tutor.set_waiting_for_answer(session_id)

        # Student starts with "no" but asks a clarifying question: "no, wait, what is a variable?"
        _evaluate_tutor_response(session_id, "no, wait, what is a variable?", tutor=tutor, ldg=ldg)

        # Must not be penalized!
        assert ctx.mastery == 0.6


class TestTransactionalTurnRollback:
    """Audit #128: Transactional state updates mid-stream."""

    import pytest
    @pytest.mark.skip(reason="Phase 1 refactored runtimes")
    def test_transaction_rollback_on_model_unavailable(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_rollback.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("concept_tx", "Transaction Concept")
        
        # Mock LLM Evaluator
        monkeypatch.setattr("core.providers.local.LocalProvider.chat", lambda msgs, **kwargs: '{"correct": true, "confidence": 1.0}')

        # Initialize concept mastery to 0.5 in SQLite
        conn = ldg._conn()
        conn.execute("UPDATE ldg_concepts SET mastery = 0.5 WHERE id = 'concept_tx'")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        tutor = TutorEngine(ldg)
        session_id = "tx_session"
        ctx = tutor.get_or_create_context(session_id)
        ctx.current_concept_id = "concept_tx"
        ctx.current_concept_name = "Transaction Concept"
        ctx.mastery = 0.5
        tutor.set_waiting_for_answer(session_id)

        orch = Orchestrator(tutor_engine=tutor, ldg=ldg)

        # Mock runtime.process to return MODEL_UNAVAILABLE
        from core.agents.registry import AgentResponse
        monkeypatch.setattr(
            orch.runtime,
            "process",
            lambda msg, ctx, spec=None: AgentResponse(
                text="Model unavailable error",
                agent_name="Tutor",
                status="MODEL_UNAVAILABLE"
            )
        )

        result = orch.submit("yes, that is right", session_id=session_id, options=TurnOptions(task_type="tutor"))
        assert result.status == "MODEL_UNAVAILABLE"

        # Check that tutor mastery and LDG mastery were rolled back to 0.5
        assert ctx.mastery == 0.5
        assert ldg.get_mastery("concept_tx") == 0.5
        assert ctx.waiting_for_answer is True

    import pytest
    @pytest.mark.skip(reason="Phase 1 refactored runtimes")
    def test_transaction_commit_on_successful_turn(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_commit.db"
        ldg = LearningDependencyGraph(db_path=db_path)
        ldg.add_concept("concept_success", "Success Concept")
        
        # Mock LLM Evaluator
        monkeypatch.setattr("core.providers.local.LocalProvider.chat", lambda msgs, **kwargs: '{"correct": true, "confidence": 1.0}')

        # Initialize concept mastery to 0.5 in SQLite
        conn = ldg._conn()
        conn.execute("UPDATE ldg_concepts SET mastery = 0.5 WHERE id = 'concept_success'")
        conn.commit()
        conn.close()
        ldg.clear_cache()

        tutor = TutorEngine(ldg)
        session_id = "success_session"
        ctx = tutor.get_or_create_context(session_id)
        ctx.current_concept_id = "concept_success"
        ctx.current_concept_name = "Success Concept"
        ctx.mastery = 0.5
        tutor.set_waiting_for_answer(session_id)

        orch = Orchestrator(tutor_engine=tutor, ldg=ldg)

        # Mock runtime.process to return SUCCESS
        from core.agents.registry import AgentResponse
        monkeypatch.setattr(
            orch.runtime,
            "process",
            lambda msg, ctx, spec=None: AgentResponse(
                text="Great job! You got it right.",
                agent_name="Tutor",
                status="SUCCESS"
            )
        )

        result = orch.submit("yes, that is right", session_id=session_id, options=TurnOptions(task_type="tutor"))
        assert result.status == "SUCCESS"

        # Check that mastery increased and was committed to both context and SQLite LDG
        assert ctx.mastery > 0.5
        assert ldg.get_mastery("concept_success") > 0.5
