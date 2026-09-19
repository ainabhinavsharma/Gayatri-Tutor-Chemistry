"""Phase 9 Test Suite: Progress and Analytics Service.

Verifies single authoritative progress API, status labels, domain breakdowns,
and analytics derived strictly from persisted evidence (P9-T01 through P9-T03).
"""
import pytest
import tempfile
from pathlib import Path

from core.learning.progress import ProgressService, get_status_label
from core.tutor.state import TutorStateManager


@pytest.fixture
def temp_state_manager():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    sm = TutorStateManager(db_path=db_path)
    yield sm
    try:
        Path(db_path).unlink()
    except Exception:
        pass


def test_status_labels():
    assert get_status_label(0.0, exposure_count=0, is_due=False) == "NEW"
    assert get_status_label(0.4, exposure_count=2, is_due=False) == "LEARNING"
    assert get_status_label(0.5, exposure_count=5, is_due=False) == "PRACTICING"
    assert get_status_label(0.75, exposure_count=5, is_due=False) == "PROFICIENT"
    assert get_status_label(0.90, exposure_count=5, is_due=False) == "MASTERED"
    assert get_status_label(0.90, exposure_count=5, is_due=True) == "REVIEW_DUE"


def test_progress_service_summary(temp_state_manager):
    service = ProgressService(state_manager=temp_state_manager)

    # Insert sample student mastery records
    temp_state_manager.conn.execute('''
        INSERT INTO student_concept_mastery (
            student_id, concept_id, mastery, confidence, exposure_count, correct_count, error_count
        ) VALUES
        ('student_p9', 'thermo.hess_law', 0.88, 0.8, 5, 4, 1),
        ('student_p9', 'inorganic.periodicity', 0.60, 0.5, 4, 2, 2)
    ''')

    summary = service.get_student_progress_summary('student_p9', temp_state_manager)

    assert summary['student_id'] == 'student_p9'
    assert 'Thermodynamics' in summary['domain_mastery']
    assert 'Inorganic Chemistry' in summary['domain_mastery']
    assert summary['domain_mastery']['Thermodynamics'] == 0.88
    assert summary['domain_mastery']['Inorganic Chemistry'] == 0.60
    assert summary['overall_mastery'] == 0.74

    hess_progress = service.get_concept_progress('student_p9', 'thermo.hess_law', temp_state_manager)
    assert hess_progress['status'] == 'MASTERED'
    assert hess_progress['accuracy'] == 0.8
