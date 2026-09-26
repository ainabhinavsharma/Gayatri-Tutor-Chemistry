"""Phase 5: Knowledge Graph + Chemistry-Aware RAG Tests.

Verifies:
1. Chemistry Entity Normalization (LaTeX to Unicode, Chemical formulas, Units, Ions).
2. Knowledge Graph typed relationships (depends_on, prerequisite, formula_for, related_to).
3. Multi-hop Graph Traversal RAG Integration (Current Concept -> Prerequisite -> Dependents).
4. DAG cycle detection and graph integrity validation.
5. Graph-based question traversal path accuracy.
"""
from __future__ import annotations

import pytest

from core.knowledge_graph import Concept, LearningDependencyGraph, RelationshipType
from core.learning.chemistry_entities import ChemistryEntityNormalizer


def test_chemistry_entity_normalization():
    """Verify LaTeX to Unicode conversion, formula subscripts, and entity extraction."""
    latex_input = r"Calculate \Delta G^\circ when \Delta H = -100 kJ/mol and \Delta S = 50 J/K mol"
    normalized = ChemistryEntityNormalizer.normalize_latex(latex_input)

    assert "ΔG°" in normalized
    assert "ΔH" in normalized
    assert "ΔS" in normalized

    formatted_formula = ChemistryEntityNormalizer.format_chemical_formula("H2O")
    assert formatted_formula == "H₂O"

    formatted_ion = ChemistryEntityNormalizer.format_chemical_formula("SO4 2-")
    assert "²⁻" in formatted_ion

    entities = ChemistryEntityNormalizer.extract_entities(normalized)
    types = [e.entity_type for e in entities]
    assert "formula" in types or "unit" in types


def test_knowledge_graph_typed_relationships(tmp_path):
    """Verify typed relationship insertion and query in LearningDependencyGraph."""
    db_path = tmp_path / "test_kg_rel.db"
    graph = LearningDependencyGraph(db_path=db_path)

    graph.add_concept("THERMO_ENTHALPY", "Enthalpy", "Heat content")
    graph.add_concept("THERMO_ENTROPY", "Entropy", "Disorder measure")
    graph.add_concept("THERMO_GIBBS", "Gibbs Free Energy", "Spontaneity indicator")

    graph.add_relationship("THERMO_GIBBS", "THERMO_ENTHALPY", relation_type=RelationshipType.DEPENDS_ON)
    graph.add_relationship("THERMO_GIBBS", "THERMO_ENTROPY", relation_type=RelationshipType.DEPENDS_ON)

    rels = graph.get_relationships("THERMO_GIBBS")
    assert len(rels) == 2
    target_ids = [r.target_id for r in rels]
    assert "THERMO_ENTHALPY" in target_ids
    assert "THERMO_ENTROPY" in target_ids


def test_multi_hop_graph_traversal(tmp_path):
    """Verify traverse_concept_graph returns multi-hop relationship path."""
    db_path = tmp_path / "test_kg_traverse.db"
    graph = LearningDependencyGraph(db_path=db_path)

    graph.add_concept("THERMO_HEAT", "Heat & Work", "Energy transfer")
    graph.add_concept("THERMO_INTERNAL_ENERGY", "Internal Energy", "Microscopic energy")
    graph.add_concept("THERMO_FIRST_LAW", "First Law", "Energy conservation")

    graph.add_relationship("THERMO_FIRST_LAW", "THERMO_HEAT", relation_type=RelationshipType.PREREQUISITE)
    graph.add_relationship("THERMO_FIRST_LAW", "THERMO_INTERNAL_ENERGY", relation_type=RelationshipType.PREREQUISITE)

    traversal = graph.traverse_concept_graph("THERMO_FIRST_LAW")
    assert traversal["found"] is True
    assert len(traversal["prerequisites"]) == 2
    assert "THERMO_HEAT" in traversal["traversal_path"]
    assert "THERMO_INTERNAL_ENERGY" in traversal["traversal_path"]


def test_graph_integrity_and_cycle_prevention(tmp_path):
    """Verify graph integrity validation and cycle prevention."""
    db_path = tmp_path / "test_kg_integrity.db"
    graph = LearningDependencyGraph(db_path=db_path)

    graph.add_concept("C1", "Concept 1")
    graph.add_concept("C2", "Concept 2")
    graph.add_relationship("C2", "C1", relation_type=RelationshipType.PREREQUISITE)

    # Attempt cycle: C1 requires C2 (C2 already requires C1)
    with pytest.raises(ValueError, match="cycle"):
        graph.add_relationship("C1", "C2", relation_type=RelationshipType.PREREQUISITE)

    integrity = graph.validate_graph_integrity()
    assert integrity["is_valid_dag"] is True
    assert integrity["cycles_detected"] == 0
