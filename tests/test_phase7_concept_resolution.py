"""Tests for Phase 7: Active Concept Resolution (Section 13).

Verifies that the runtime dynamically resolves:
- domain
- chapter
- topic
- subtopic
- concept_id

Using:
1. Explicit user request (message keywords)
2. Recent context (conversation turn history)
3. Active session concept (active_concept_id)
4. Active learning state (from state_manager)
5. No hard-coded active learner state (empty/unknown queries return undetermined fallback)

Mandatory test cases from Section 13:
- Hess's Law → Thermodynamics
- Gibbs free energy → Thermodynamics
- Ionization enthalpy → Inorganic Chemistry
- Electronic configuration → Inorganic Chemistry
"""
import pytest
from core.curriculum.resolver import ConceptResolver, ResolvedConcept
from core.tutor.state import TutorStateManager, LearningEvent


def test_hesss_law_resolves_to_thermodynamics():
    """Mandatory Section 13 test: Hess's Law → Thermodynamics."""
    queries = [
        "What is Hess's Law?",
        "Can you explain Hess's law of constant heat summation?",
        "Solve a problem using Hess law",
    ]
    for q in queries:
        res = ConceptResolver.resolve_concept(q)
        assert res.domain == "Thermodynamics", f"Expected Thermodynamics for query: '{q}', got '{res.domain}'"
        assert res.chapter == "Thermodynamics"
        assert "Hess" in res.topic
        assert res.concept_id == "chem_thermo_hess"
        assert res.confidence >= 0.8


def test_gibbs_free_energy_resolves_to_thermodynamics():
    """Mandatory Section 13 test: Gibbs free energy → Thermodynamics."""
    queries = [
        "Explain Gibbs free energy criterion for spontaneity",
        "Calculate delta G using Gibbs energy",
        "What is free energy in thermodynamics?",
    ]
    for q in queries:
        res = ConceptResolver.resolve_concept(q)
        assert res.domain == "Thermodynamics", f"Expected Thermodynamics for query: '{q}', got '{res.domain}'"
        assert res.chapter == "Thermodynamics"
        assert "Gibbs" in res.topic
        assert res.concept_id == "chem_thermo_gibbs"
        assert res.confidence >= 0.8


def test_ionization_enthalpy_resolves_to_inorganic_chemistry():
    """Mandatory Section 13 test: Ionization enthalpy → Inorganic Chemistry."""
    queries = [
        "Why does ionization enthalpy increase across a period?",
        "Explain the trend in ionization energy",
        "What is enthalpy of ionization in periodic table?",
    ]
    for q in queries:
        res = ConceptResolver.resolve_concept(q)
        assert res.domain == "Inorganic Chemistry", f"Expected Inorganic Chemistry for query: '{q}', got '{res.domain}'"
        assert "Classification of Elements" in res.chapter or "Periodicity" in res.chapter
        assert "Periodic Table Trends" in res.topic
        assert res.concept_id == "chem_inorg_periodic"
        assert res.confidence >= 0.8


def test_electronic_configuration_resolves_to_inorganic_chemistry():
    """Mandatory Section 13 test: Electronic configuration → Inorganic Chemistry."""
    queries = [
        "What is the electronic configuration of Chromium?",
        "Explain Aufbau principle and electronic structure",
        "How do valence electrons determine electronic configuration?",
    ]
    for q in queries:
        res = ConceptResolver.resolve_concept(q)
        assert res.domain == "Inorganic Chemistry", f"Expected Inorganic Chemistry for query: '{q}', got '{res.domain}'"
        assert "Structure of Atom" in res.chapter or "Periodicity" in res.chapter
        assert "Electronic Configuration" in res.topic
        assert res.concept_id == "chem_inorg_electronic"
        assert res.confidence >= 0.8


def test_recent_context_resolution():
    """Verify resolution from recent conversation context when user message is brief/ambiguous."""
    # User message contains no domain keywords, but recent context does
    res = ConceptResolver.resolve_concept(
        user_message="Can you give me a practice problem on this?",
        recent_context=[
            "Let's study the Aufbau principle and quantum numbers.",
            "Sure, how do orbitals get filled?",
        ],
    )
    assert res.domain == "Inorganic Chemistry"
    assert res.concept_id == "chem_inorg_electronic"
    assert res.confidence == 0.8


def test_active_concept_id_retention():
    """Verify active_concept_id retains current concept when user message has no keywords."""
    res = ConceptResolver.resolve_concept(
        user_message="Tell me more about it",
        active_concept_id="chem_thermo_hess",
    )
    assert res.domain == "Thermodynamics"
    assert res.concept_id == "chem_thermo_hess"
    assert res.confidence == 0.7


def test_student_learning_state_resolution(tmp_path):
    """Verify resolution falls back to student's active learning history from TutorStateManager."""
    db_path = str(tmp_path / "test_concept_state.db")
    sm = TutorStateManager(db_path)

    # Record a learning event for a student in Inorganic Chemistry
    event = LearningEvent(
        event_id="evt_res_01",
        student_id="student_res",
        session_id="sess_res",
        turn_id="turn_res",
        concept_id="chem_inorg_bonding",
        correctness="correct",
    )
    sm.record_learning_event(event)

    # Resolve without keywords, context, or active_concept_id
    res = ConceptResolver.resolve_concept(
        user_message="I'm ready to continue where I left off",
        student_id="student_res",
        state_manager=sm,
    )
    assert res.domain == "Inorganic Chemistry"
    assert res.concept_id == "chem_inorg_bonding"
    assert res.topic == "Chemical Bonding"
    assert res.confidence == 0.6


def test_no_hardcoded_active_learner_state():
    """Verify empty/unrelated message with no context returns Undetermined rather than pinning to Thermodynamics."""
    res = ConceptResolver.resolve_concept(user_message="Hello, who are you?")
    assert res.domain == "Undetermined"
    assert res.concept_id == "chem_general_undetermined"
    assert res.confidence == 0.3
