"""Gayatri AI - Phase 3 Acceptance Test Suite.

Tests dynamic chemistry concept & topic resolution:
- Inorganic Chemistry resolution (ionization enthalpy, periodic table, bonding, stoichiometry)
- Thermodynamics resolution (Hess's law, Gibbs free energy, entropy, enthalpy)
- Active concept persistence across multi-turn sessions
- Explicit topic override over active session concept
"""

import pytest
from core.curriculum.resolver import ConceptResolver, ResolvedConcept


def test_resolve_inorganic_ionization_enthalpy():
    """P3-T01 & P3 Acceptance: 'ionization enthalpy' resolves to Inorganic Chemistry."""
    res = ConceptResolver.resolve_concept("Explain ionization enthalpy and its trends across periods.")
    assert res.domain == "Inorganic Chemistry"
    assert res.topic == "Periodic Table Trends"
    assert res.concept_id == "chem_inorg_periodic"
    assert res.confidence >= 0.8


def test_resolve_thermo_hess_law():
    """P3-T01: 'Hess's law' resolves to Thermodynamics."""
    res = ConceptResolver.resolve_concept("Can you teach me about Hess's law of constant heat summation?")
    assert res.domain == "Thermodynamics"
    assert res.topic == "Hess Law"
    assert res.concept_id == "chem_thermo_hess"


def test_resolve_thermo_gibbs():
    """P3-T01: 'Gibbs free energy' resolves to Thermodynamics."""
    res = ConceptResolver.resolve_concept("What is Gibbs free energy and how does it determine spontaneity?")
    assert res.domain == "Thermodynamics"
    assert res.topic == "Gibbs Free Energy"
    assert res.concept_id == "chem_thermo_gibbs"


def test_active_concept_persists_across_turns():
    """P3-T02: Retains active concept when message contains no explicit keyword."""
    res = ConceptResolver.resolve_concept("Can you explain that more simply?", active_concept_id="chem_inorg_periodic")
    assert res.domain == "Inorganic Chemistry"
    assert res.concept_id == "chem_inorg_periodic"
    assert res.confidence >= 0.7


def test_new_explicit_topic_overrides_active_topic():
    """P3-T03: New explicit topic overrides active session concept."""
    res = ConceptResolver.resolve_concept("Let us move to Hess's law now", active_concept_id="chem_inorg_periodic")
    assert res.domain == "Thermodynamics"
    assert res.concept_id == "chem_thermo_hess"
