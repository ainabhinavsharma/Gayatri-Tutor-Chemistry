"""Phase 11 Test Suite: Curriculum Structural Validation.

Verifies structural integrity, cycle detection, missing prerequisite catching,
and difficulty bounds validation (P11-T01 through P11-T04).
"""
import pytest
from core.curriculum.validator import CurriculumValidator


def test_valid_curriculum():
    validator = CurriculumValidator()
    concepts = [
        {"id": "thermo.first_law", "name": "First Law", "difficulty": 2, "domain": "Thermodynamics"},
        {"id": "thermo.enthalpy", "name": "Enthalpy", "difficulty": 3, "prerequisites": ["thermo.first_law"], "domain": "Thermodynamics"},
        {"id": "thermo.hess_law", "name": "Hess Law", "difficulty": 3, "prerequisites": ["thermo.enthalpy"], "domain": "Thermodynamics"},
    ]

    res = validator.validate_concepts(concepts)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_duplicate_concept_id():
    validator = CurriculumValidator()
    concepts = [
        {"id": "thermo.hess", "difficulty": 2},
        {"id": "thermo.hess", "difficulty": 3},
    ]

    res = validator.validate_concepts(concepts)
    assert res.is_valid is False
    assert any("Duplicate" in err for err in res.errors)


def test_missing_prerequisite():
    validator = CurriculumValidator()
    concepts = [
        {"id": "thermo.hess", "difficulty": 3, "prerequisites": ["thermo.non_existent"]},
    ]

    res = validator.validate_concepts(concepts)
    assert res.is_valid is False
    assert any("missing prerequisite" in err for err in res.errors)


def test_prerequisite_cycle_detection():
    validator = CurriculumValidator()
    # A -> B -> C -> A (cycle)
    concepts = [
        {"id": "c_a", "prerequisites": ["c_c"]},
        {"id": "c_b", "prerequisites": ["c_a"]},
        {"id": "c_c", "prerequisites": ["c_b"]},
    ]

    res = validator.validate_concepts(concepts)
    assert res.is_valid is False
    assert any("cycle detected" in err.lower() for err in res.errors)


def test_invalid_difficulty_level():
    validator = CurriculumValidator()
    concepts = [
        {"id": "c_1", "difficulty": 99},  # Out of range 1..5
    ]

    res = validator.validate_concepts(concepts)
    assert res.is_valid is False
    assert any("invalid difficulty" in err for err in res.errors)
