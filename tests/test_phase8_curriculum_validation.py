"""Tests for Phase 8: Curriculum Validation Re-Audit (P11-T01 to P11-T05)."""
import pytest
from core.curriculum.validator import CurriculumValidator, CurriculumValidationResult


def test_valid_curriculum():
    """Test valid curriculum definition with linear prerequisites."""
    concepts = [
        {
            "id": "thermo.first_law",
            "name": "First Law of Thermodynamics",
            "domain": "Thermodynamics",
            "difficulty": 2,
            "prerequisites": [],
        },
        {
            "id": "thermo.hess_law",
            "name": "Hess Law",
            "domain": "Thermodynamics",
            "difficulty": 3,
            "prerequisites": ["thermo.first_law"],
        },
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.concept_count == 2


def test_duplicate_concept_id():
    """Test detection of duplicate concept IDs."""
    concepts = [
        {"id": "concept_a", "difficulty": 2, "prerequisites": []},
        {"id": "concept_a", "difficulty": 3, "prerequisites": []},
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is False
    assert any("Duplicate concept ID" in err for err in result.errors)


def test_missing_prerequisite():
    """Test detection of referenced prerequisite IDs that do not exist."""
    concepts = [
        {"id": "concept_b", "difficulty": 3, "prerequisites": ["non_existent_id"]},
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is False
    assert any("references missing prerequisite ID" in err for err in result.errors)


def test_prerequisite_cycle_detection():
    """Test DAG validation catching cyclic prerequisite dependencies (e.g. A -> B -> A)."""
    concepts = [
        {"id": "concept_a", "difficulty": 2, "prerequisites": ["concept_b"]},
        {"id": "concept_b", "difficulty": 3, "prerequisites": ["concept_a"]},
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is False
    assert any("Prerequisite cycle detected" in err for err in result.errors)


def test_invalid_difficulty_level():
    """Test detection of out-of-range difficulty values (outside 1..5)."""
    concepts = [
        {"id": "concept_high", "difficulty": 6, "prerequisites": []},
        {"id": "concept_zero", "difficulty": 0, "prerequisites": []},
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is False
    assert any("invalid difficulty" in err for err in result.errors)


def test_orphan_concept_warning():
    """Test warning generation for orphan concepts."""
    concepts = [
        {"id": "concept_root", "difficulty": 2, "prerequisites": []},
        {"id": "concept_child", "difficulty": 3, "prerequisites": ["concept_root"]},
        {"id": "concept_orphan", "difficulty": 2, "prerequisites": []},
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is True
    assert len(result.warnings) > 0
    assert any("Orphan concept detected" in warn for warn in result.warnings)
