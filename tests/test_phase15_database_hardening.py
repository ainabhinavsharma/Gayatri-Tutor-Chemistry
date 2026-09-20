"""Phase 15: Database Hardening Verification Tests (Section 21).

Verifies:
1. Foreign key enforcement (`PRAGMA foreign_keys = ON`) and cascade deletions.
2. Unique constraints and conflict resolution/idempotency.
3. Transaction atomicity and rollback safety (zero partial writes on failure).
4. Database retry resilience (`with_db_retry` / `execute_with_retry`) on transient lock errors.
5. Schema version tracking via `PRAGMA user_version` and incremental migrations.
6. Core invariant: "Never show successful progress if the learning update failed."
"""
import sqlite3
from unittest.mock import MagicMock
import pytest

from core.db import get_safe_db_connection, run_migrations, with_db_retry, execute_with_retry
from core.tutor.state import TutorStateManager, LearningEvent
from core.rag.store import RAGStore
from core.rag.schema import DocumentChunk, SourceMetadata
from core.learning.progress import ProgressService
from core.orchestrator import Orchestrator, TurnOptions


def test_foreign_key_enforcement_and_cascade(tmp_path):
    """Verify Section 21: foreign keys are strictly enforced and cascades work."""
    db_path = tmp_path / "test_fk.db"
    store = RAGStore(db_path=db_path)

    # 1. Attempting to insert a chunk referencing non-existent source_id must fail
    orphan_chunk = DocumentChunk(
        chunk_id="chunk_orphan_01",
        source_id="nonexistent_source_id",
        chapter="Thermodynamics",
        topic="Enthalpy",
        subtopic="Standard",
        page=100,
        text="Sample text",
    )

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        with store.conn:
            prov = orphan_chunk.provenance_type.value if hasattr(orphan_chunk.provenance_type, 'value') else str(orphan_chunk.provenance_type)
            store.conn.execute("""
                INSERT INTO rag_chunks (chunk_id, source_id, chapter, topic, subtopic, page, section, text, provenance_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                orphan_chunk.chunk_id, orphan_chunk.source_id, orphan_chunk.chapter,
                orphan_chunk.topic, orphan_chunk.subtopic, orphan_chunk.page,
                orphan_chunk.section, orphan_chunk.text, prov
            ))

    # 2. Insert valid source first, then insert chunk -> succeeds
    source = SourceMetadata(
        source_id="valid_ncert_source",
        title="NCERT Class 11 Chemistry",
        class_level="11",
        chapter="Thermodynamics",
    )
    store.add_source(source)

    valid_chunk = DocumentChunk(
        chunk_id="chunk_valid_01",
        source_id="valid_ncert_source",
        chapter="Thermodynamics",
        topic="Enthalpy",
        subtopic="Standard",
        page=100,
        text="Valid chunk text",
    )
    store.add_chunks([valid_chunk])

    # Verify chunk was stored
    retrieved = store.get_all_chunks()
    assert len(retrieved) == 1
    assert retrieved[0].chunk_id == "chunk_valid_01"

    # 3. Delete source -> verify CASCADE deletes the chunk
    with store.conn:
        store.conn.execute("DELETE FROM rag_sources WHERE source_id = ?", ("valid_ncert_source",))

    remaining_chunks = store.get_all_chunks()
    assert len(remaining_chunks) == 0


def test_unique_constraints_and_idempotency(tmp_path):
    """Verify Section 21: unique constraints and idempotent updates prevent data duplication."""
    db_path = tmp_path / "test_unique.db"
    state_mgr = TutorStateManager(db_path=db_path)

    event = LearningEvent(
        event_id="evt_unique_test",
        student_id="student_u1",
        session_id="sess_u1",
        turn_id="turn_u1",
        concept_id="chem.thermo.enthalpy",
        difficulty=0.5,
        question_type="conceptual",
        correctness="correct",
        confidence=0.9,
    )

    # First write succeeds
    assert state_mgr.record_learning_event(event) is True

    # Duplicate write returns False and does not duplicate
    assert state_mgr.record_learning_event(event) is False

    count = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM learning_events WHERE event_id = ?", ("evt_unique_test",)
    ).fetchone()["cnt"]
    assert count == 1

    # student_concept_mastery primary key (student_id, concept_id) has exactly 1 row
    mastery_rows = state_mgr.conn.execute(
        "SELECT COUNT(*) as cnt FROM student_concept_mastery WHERE student_id = ? AND concept_id = ?",
        ("student_u1", "chem.thermo.enthalpy")
    ).fetchone()["cnt"]
    assert mastery_rows == 1


def test_transaction_atomicity_and_partial_write_rollback(tmp_path):
    """Verify Section 21: transactions rollback completely on failure; zero partial writes."""
    db_path = tmp_path / "test_atomicity.db"
    state_mgr = TutorStateManager(db_path=db_path)

    # Simulate an atomic transaction where an error occurs midway
    try:
        with state_mgr.conn:
            state_mgr.conn.execute("""
                INSERT INTO learning_events (
                    event_id, student_id, session_id, turn_id, concept_id, timestamp, correctness
                ) VALUES ('evt_atomic_1', 's_atomic', 'sess_at', 'turn_at', 'c1', '2026-09-20', 'correct')
            """)
            # Second statement deliberately fails
            raise sqlite3.OperationalError("Simulated mid-transaction failure")
    except sqlite3.OperationalError:
        pass

    # Verify first statement was rolled back completely
    row = state_mgr.conn.execute(
        "SELECT * FROM learning_events WHERE event_id = 'evt_atomic_1'"
    ).fetchone()
    assert row is None


def test_database_retry_on_locked():
    """Verify Section 21: with_db_retry / execute_with_retry transparently recovers from transient locks."""
    call_count = 0

    def flaky_db_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise sqlite3.OperationalError("database is locked")
        return "success_recovered"

    result = execute_with_retry(flaky_db_operation, max_retries=3, base_delay=0.01)
    assert result == "success_recovered"
    assert call_count == 3

    # Non-lock errors should NOT be retried
    non_lock_count = 0

    def syntax_error_operation():
        nonlocal non_lock_count
        non_lock_count += 1
        raise sqlite3.OperationalError("near 'SYNTAX': syntax error")

    with pytest.raises(sqlite3.OperationalError, match="syntax error"):
        execute_with_retry(syntax_error_operation, max_retries=3, base_delay=0.01)

    assert non_lock_count == 1


def test_schema_migrations_version_tracking(tmp_path):
    """Verify Section 21: schema migrations track PRAGMA user_version and are idempotent."""
    db_path = tmp_path / "test_migration_tracking.db"
    conn = get_safe_db_connection(db_path)

    try:
        executed_steps = []

        def step_1(c):
            executed_steps.append(1)
            c.execute("CREATE TABLE t_step1 (id INT PRIMARY KEY);")

        def step_2(c):
            executed_steps.append(2)
            c.execute("CREATE TABLE t_step2 (name TEXT);")

        migrations = {
            1: ("step_1", step_1),
            2: ("step_2", step_2),
        }

        v = run_migrations(conn, migrations)
        assert v == 2
        assert executed_steps == [1, 2]

        user_v = conn.execute("PRAGMA user_version;").fetchone()[0]
        assert user_v == 2

        # Re-running migrations is completely idempotent
        v_rerun = run_migrations(conn, migrations)
        assert v_rerun == 2
        assert executed_steps == [1, 2]  # No additional executions
    finally:
        conn.close()


def test_never_show_successful_progress_if_learning_update_failed(tmp_path):
    """Verify Section 21 invariant: 'Never show successful progress if the learning update failed.'"""
    db_path = tmp_path / "test_progress_invariant.db"
    state_mgr = TutorStateManager(db_path=db_path)
    progress_svc = ProgressService(state_manager=state_mgr)

    # Initial state: student has 0 exposure and NEW status
    prog_before = progress_svc.get_concept_progress("student_fail_test", "thermo.enthalpy")
    assert prog_before["exposure_count"] == 0
    assert prog_before["mastery"] == 0.0
    assert prog_before["status"] == "NEW"

    # Attempt to record invalid event (invalid correctness value)
    bad_event = LearningEvent(
        event_id="evt_bad_01",
        student_id="student_fail_test",
        session_id="sess_fail",
        turn_id="turn_fail",
        concept_id="thermo.enthalpy",
        correctness="bogus_correctness",  # Invalid
    )

    with pytest.raises(ValueError, match="must be one of"):
        state_mgr.record_learning_event(bad_event)

    # Progress must NOT have updated
    prog_after = progress_svc.get_concept_progress("student_fail_test", "thermo.enthalpy")
    assert prog_after["exposure_count"] == 0
    assert prog_after["mastery"] == 0.0
    assert prog_after["status"] == "NEW"

    # In orchestrator: if turn fails, response status is ERROR, not SUCCESS
    orch = Orchestrator(state_manager=state_mgr)
    opts = TurnOptions(mode="chemistry_tutor", student_id="student_fail_test")

    # Pass an invalid mode to trigger submit error
    bad_opts = TurnOptions(mode="nonexistent_mode", student_id="student_fail_test")
    res = orch.submit("What is enthalpy?", session_id="sess_fail", options=bad_opts)
    assert res.status == "ERROR"
    assert "error" in res.text.lower()
