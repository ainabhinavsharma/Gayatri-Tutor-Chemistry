"""Tests for Teacher and Parent Governance Controls (Phase 4)."""

import json
from pathlib import Path
from core.governance import GovernanceManager
from core.knowledge_graph import LearningDependencyGraph


def test_governance_pin_verification_and_update(tmp_path: Path):
    """Verify parental PIN security and update flow."""
    db_path = tmp_path / "gov_test.db"
    gov = GovernanceManager(db_path)

    assert gov.verify_pin("1234") is True
    assert gov.verify_pin("wrong") is False

    # Update PIN
    assert gov.set_pin("wrong", "9999") is False
    assert gov.set_pin("1234", "9999") is True

    assert gov.verify_pin("9999") is True
    assert gov.verify_pin("1234") is False


def test_governance_time_limits(tmp_path: Path):
    """Verify daily learning time tracking and cutoff limits."""
    db_path = tmp_path / "gov_time_test.db"
    gov = GovernanceManager(db_path)

    profile_id = "user_time_1"
    assert gov.check_time_limit(profile_id, daily_limit_minutes=60.0) is True

    # Record 45 minutes
    gov.record_usage(profile_id, minutes=45.0)
    assert gov.check_time_limit(profile_id, daily_limit_minutes=60.0) is True

    # Record another 20 minutes (total 65m > 60m limit)
    gov.record_usage(profile_id, minutes=20.0)
    assert gov.check_time_limit(profile_id, daily_limit_minutes=60.0) is False


def test_governance_student_report_export(tmp_path: Path):
    """Verify exporting student mastery reports in JSON and CSV formats."""
    db_path = tmp_path / "gov_report_test.db"
    gov = GovernanceManager(db_path)

    ldg = LearningDependencyGraph(db_path=db_path)
    ldg.add_concept("c1", "Algebra", subject="math")
    ldg.add_concept("c2", "Geometry", subject="math")

    # Mark c1 as mastered
    ldg.record_attempt("c1", correct=True, confidence=1.0)
    ldg.record_attempt("c1", correct=True, confidence=1.0)
    ldg.record_attempt("c1", correct=True, confidence=1.0)

    json_report = gov.export_progress_report("u1", "Aarav", ldg, format="json")
    parsed = json.loads(json_report)
    assert parsed["student_name"] == "Aarav"
    assert parsed["total_concepts"] == 2
    assert len(parsed["concepts"]) == 2

    csv_report = gov.export_progress_report("u1", "Aarav", ldg, format="csv")
    assert "Concept ID,Name,Subject,Mastery,Exposures,Status" in csv_report
    assert "Algebra" in csv_report
