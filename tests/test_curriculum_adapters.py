"""Tests for CBSE and NCERT curriculum adapters (Phase 4)."""

from pathlib import Path
from core.curriculum.adapters import CBSECurriculumAdapter, NCERTCurriculumAdapter
from core.knowledge_graph import LearningDependencyGraph


def test_cbse_math_curriculum_adapter(tmp_path: Path):
    """Verify loading CBSE Grade 9 Math curriculum into LDG."""
    adapter = CBSECurriculumAdapter.for_subject_and_grade("math", "grade9")
    assert adapter.board == "CBSE"
    assert adapter.subject == "Mathematics"

    ldg = LearningDependencyGraph(db_path=tmp_path / "cbse_test.db")
    loaded_count = adapter.load_into_graph(ldg)
    assert loaded_count >= 3

    # Verify prerequisite relationship: Polynomials requires Number Systems
    prereqs = ldg.get_prerequisites("cbse_math_9_polynomials")
    assert "cbse_math_9_number_systems" in prereqs

    # Verify initial unlock state: Number Systems unlocked, Polynomials locked
    assert ldg.is_unlocked("cbse_math_9_number_systems") is True
    assert ldg.is_unlocked("cbse_math_9_polynomials") is False


def test_ncert_science_curriculum_adapter(tmp_path: Path):
    """Verify loading NCERT Grade 9 Science curriculum with multilingual support."""
    adapter = NCERTCurriculumAdapter.for_subject_and_grade("science", "grade9")
    assert adapter.board == "NCERT"
    assert adapter.subject == "Science"

    # Test Hindi localization
    hindi_concepts = adapter.get_concepts(lang="hi")
    motion = next(c for c in hindi_concepts if c["id"] == "ncert_sci_9_motion")
    assert motion["localized_name"] == "गति"

    # Load Hindi concepts into graph
    ldg = LearningDependencyGraph(db_path=tmp_path / "ncert_test.db")
    adapter.load_into_graph(ldg, lang="hi")

    concept_node = ldg.get_concept("ncert_sci_9_motion")
    assert concept_node is not None
    assert concept_node.name == "गति"
