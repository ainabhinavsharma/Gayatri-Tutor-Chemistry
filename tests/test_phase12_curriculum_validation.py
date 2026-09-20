"""Phase 12: Curriculum & Learning Dependency Graph (LDG) Validation Tests (Section 18).

Verifies:
1. Unique concept IDs (no duplicates).
2. Valid prerequisite IDs (stable programmatic identifiers, rejecting free text).
3. No prerequisite cycles (strict DAG cycle detection).
4. No orphan prerequisites (dangling prerequisite IDs) and detection of orphan concepts.
5. Valid domains and difficulty levels (1..5 or normalized 0.0..1.0).
6. Learning outcomes and question mappings presence.
7. CI failure enforcement on curriculum corruption (CurriculumCorruptionError via validate_or_raise).
8. Integrity of production curriculum file (ncert_class11_12.json).
"""
import pytest
from pathlib import Path
from core.curriculum.validator import (
    CurriculumValidator,
    CurriculumValidationResult,
    CurriculumCorruptionError,
)

CANONICAL_NCERT_FILE = (
    Path(__file__).parent.parent / "data" / "curriculum" / "chemistry" / "ncert_class11_12.json"
)


def test_valid_curriculum_linear_dag():
    """Verify valid curriculum passes validation with proper DAG structure."""
    concepts = [
        {
            "id": "chem.first_law",
            "name": "First Law of Thermodynamics",
            "domain": "Thermodynamics",
            "difficulty": 2,
            "description": "Conservation of energy in chemical systems",
            "learning_outcomes": ["State first law", "Calculate work and heat"],
            "assessment_types": ["conceptual", "numerical"],
            "prerequisites": [],
        },
        {
            "id": "chem.enthalpy",
            "name": "Enthalpy",
            "domain": "Thermodynamics",
            "difficulty": 3,
            "description": "Heat content at constant pressure",
            "learning_outcomes": ["Define enthalpy", "Relate delta H to delta U"],
            "assessment_types": ["conceptual", "numerical"],
            "prerequisites": ["chem.first_law"],
        },
        {
            "id": "chem.hess_law",
            "name": "Hess's Law",
            "domain": "Thermodynamics",
            "difficulty": 4,
            "description": "Constant heat summation",
            "learning_outcomes": ["Apply Hess's law to calculate reaction enthalpies"],
            "assessment_types": ["numerical"],
            "prerequisites": ["chem.enthalpy"],
        },
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.concept_count == 3


def test_duplicate_concept_ids_rejected():
    """Verify Section 18 rule: unique concept IDs (duplicate concept IDs cause validation failure)."""
    concepts = [
        {"id": "chem.thermo.01", "difficulty": 2, "prerequisites": []},
        {"id": "chem.thermo.01", "difficulty": 3, "prerequisites": []},
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is False
    assert any("Duplicate concept ID found" in err for err in result.errors)


def test_stable_prerequisite_ids_enforced_and_free_text_rejected():
    """Verify Section 18 rule: prefer stable prerequisite IDs over free text."""
    validator = CurriculumValidator()

    # Free text prerequisite with spaces and punctuation must be rejected
    free_text_concepts = [
        {
            "id": "chem.thermo.entropy",
            "difficulty": 3,
            "prerequisites": ["System and Surroundings, Chapter 6"],
        }
    ]
    result = validator.validate_concepts(free_text_concepts)
    assert result.is_valid is False
    assert any("unstable/free-text prerequisite" in err for err in result.errors)

    # Self-dependency must be rejected
    self_dep_concepts = [
        {
            "id": "chem.thermo.entropy",
            "difficulty": 3,
            "prerequisites": ["chem.thermo.entropy"],
        }
    ]
    result_self = validator.validate_concepts(self_dep_concepts)
    assert result_self.is_valid is False
    assert any("cannot have itself as a prerequisite" in err for err in result_self.errors)


def test_missing_and_orphan_prerequisites():
    """Verify Section 18 rule: no orphan prerequisites (pointing to nonexistent IDs)."""
    concepts = [
        {
            "id": "chem.gibbs",
            "difficulty": 4,
            "prerequisites": ["chem.nonexistent_prereq"],
        }
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert result.is_valid is False
    assert any("references missing prerequisite ID" in err for err in result.errors)


def test_cycle_detection_direct_and_multi_hop():
    """Verify Section 18 rule: no cycles (DAG validation)."""
    validator = CurriculumValidator()

    # Direct 2-node cycle: A -> B -> A
    cycle_2 = [
        {"id": "concept_a", "difficulty": 2, "prerequisites": ["concept_b"]},
        {"id": "concept_b", "difficulty": 3, "prerequisites": ["concept_a"]},
    ]
    res_2 = validator.validate_concepts(cycle_2)
    assert res_2.is_valid is False
    assert any("Prerequisite cycle detected" in err for err in res_2.errors)

    # 3-node cycle: A -> B -> C -> A
    cycle_3 = [
        {"id": "node_a", "difficulty": 2, "prerequisites": ["node_b"]},
        {"id": "node_b", "difficulty": 3, "prerequisites": ["node_c"]},
        {"id": "node_c", "difficulty": 4, "prerequisites": ["node_a"]},
    ]
    res_3 = validator.validate_concepts(cycle_3)
    assert res_3.is_valid is False
    assert any("Prerequisite cycle detected" in err for err in res_3.errors)


def test_difficulty_validation_supports_discrete_and_normalized():
    """Verify Section 18 rule: valid difficulty (1..5 or normalized 0.0..1.0)."""
    validator = CurriculumValidator()

    # Valid discrete 1..5
    valid_discrete = [{"id": "c1", "difficulty": 3, "prerequisites": []}]
    assert validator.validate_concepts(valid_discrete).is_valid is True

    # Valid normalized 0.0..1.0
    valid_normalized = [{"id": "c2", "difficulty": 0.4, "prerequisites": []}]
    assert validator.validate_concepts(valid_normalized).is_valid is True

    # Invalid: > 5
    invalid_high = [{"id": "c3", "difficulty": 6, "prerequisites": []}]
    assert validator.validate_concepts(invalid_high).is_valid is False

    # Invalid: < 0
    invalid_neg = [{"id": "c4", "difficulty": -0.5, "prerequisites": []}]
    assert validator.validate_concepts(invalid_neg).is_valid is False


def test_learning_outcomes_and_question_mappings_warnings():
    """Verify Section 18: learning outcomes and question mappings checked."""
    concepts = [
        {
            "id": "chem.bare_concept",
            "difficulty": 2,
            "prerequisites": [],
            # Missing description/learning_outcomes and assessment_types/questions
        }
    ]
    validator = CurriculumValidator()
    result = validator.validate_concepts(concepts)
    assert any("missing learning outcomes or description" in warn for warn in result.warnings)
    assert any("no question mappings or assessment types defined" in warn for warn in result.warnings)


def test_ci_fail_fast_on_curriculum_corruption():
    """Verify Section 18 rule: CI must fail on curriculum corruption via CurriculumCorruptionError."""
    validator = CurriculumValidator()
    corrupted_concepts = [
        {"id": "corrupted_1", "difficulty": 10, "prerequisites": ["missing_id"]}
    ]

    with pytest.raises(CurriculumCorruptionError) as exc_info:
        validator.validate_or_raise(corrupted_concepts)

    err = exc_info.value
    assert len(err.errors) >= 2
    assert any("invalid difficulty" in e for e in err.errors)
    assert any("missing prerequisite ID" in e for e in err.errors)


def test_production_curriculum_file_integrity():
    """Verify that canonical production file data/curriculum/chemistry/ncert_class11_12.json passes validation."""
    assert CANONICAL_NCERT_FILE.exists(), f"Production curriculum file not found at {CANONICAL_NCERT_FILE}"
    validator = CurriculumValidator()

    # Must pass without raising CurriculumCorruptionError
    result = validator.validate_or_raise(CANONICAL_NCERT_FILE)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.concept_count >= 15
