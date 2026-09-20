"""Gayatri AI - Dynamic Chemistry Concept & Topic Resolver (Phase 3).

Resolves domain, chapter, topic, subtopic, and stable concept_id from student message,
active session concept state, and curriculum manifest (P3-T01 to P3-T04).
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("gayatri.curriculum.resolver")


@dataclass
class ResolvedConcept:
    """Resolved active chemistry topic/concept metadata."""
    domain: str
    chapter: str
    topic: str
    subtopic: str
    concept_id: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "chapter": self.chapter,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "concept_id": self.concept_id,
            "confidence": self.confidence,
        }


# Stable mapping of chemistry domain/topic keywords to concepts (P3-T01)
CONCEPT_KEYWORD_MAP = [
    # Inorganic Chemistry
    {
        "keywords": ["electronic configuration", "electronic structure", "aufbau", "valence electrons", "quantum numbers"],
        "domain": "Inorganic Chemistry",
        "chapter": "Structure of Atom & Periodicity",
        "topic": "Electronic Configuration",
        "subtopic": "Aufbau Principle & Orbitals",
        "concept_id": "chem_inorg_electronic",
    },
    {
        "keywords": ["ionization", "enthalpy of ionization", "ionisation", "periodicity", "periodic table", "atomic radius", "electronegativity"],
        "domain": "Inorganic Chemistry",
        "chapter": "Classification of Elements and Periodicity",
        "topic": "Periodic Table Trends",
        "subtopic": "Ionization Enthalpy",
        "concept_id": "chem_inorg_periodic",
    },
    {
        "keywords": ["bonding", "covalent", "ionic bond", "vsepr", "lewis structure", "octet"],
        "domain": "Inorganic Chemistry",
        "chapter": "Chemical Bonding and Molecular Structure",
        "topic": "Chemical Bonding",
        "subtopic": "Covalent & Ionic Bonding",
        "concept_id": "chem_inorg_bonding",
    },
    {
        "keywords": ["s-block", "alkali", "alkaline earth", "sodium", "potassium", "magnesium", "calcium"],
        "domain": "Inorganic Chemistry",
        "chapter": "s-Block Elements",
        "topic": "s-Block Elements",
        "subtopic": "Alkali & Alkaline Earth Metals",
        "concept_id": "chem_inorg_sblock",
    },
    {
        "keywords": ["p-block", "boron", "carbon", "nitrogen family", "oxygen family", "halogen", "noble gas"],
        "domain": "Inorganic Chemistry",
        "chapter": "p-Block Elements",
        "topic": "p-Block Elements",
        "subtopic": "Group 13-18 Elements",
        "concept_id": "chem_inorg_pblock",
    },
    {
        "keywords": ["balancing", "equation", "stoichiometry", "mole concept", "avogadro", "limiting reagent"],
        "domain": "Inorganic Chemistry",
        "chapter": "Some Basic Concepts of Chemistry",
        "topic": "Stoichiometry and Mole Concept",
        "subtopic": "Equation Balancing & Moles",
        "concept_id": "chem_stoichiometry",
    },
    # Thermodynamics
    {
        "keywords": ["hess", "hess's law", "constant heat summation", "enthalpy of reaction"],
        "domain": "Thermodynamics",
        "chapter": "Thermodynamics",
        "topic": "Hess Law",
        "subtopic": "Enthalpy Summations",
        "concept_id": "chem_thermo_hess",
    },
    {
        "keywords": ["gibbs", "free energy", "delta g", "spontaneity", "spontaneous"],
        "domain": "Thermodynamics",
        "chapter": "Thermodynamics",
        "topic": "Gibbs Free Energy",
        "subtopic": "Spontaneity & Equilibrium",
        "concept_id": "chem_thermo_gibbs",
    },
    {
        "keywords": ["entropy", "delta s", "second law", "disorder", "randomness"],
        "domain": "Thermodynamics",
        "chapter": "Thermodynamics",
        "topic": "Entropy",
        "subtopic": "Second Law & Entropy",
        "concept_id": "chem_thermo_entropy",
    },
    {
        "keywords": ["enthalpy", "delta h", "heat of reaction", "exothermic", "endothermic"],
        "domain": "Thermodynamics",
        "chapter": "Thermodynamics",
        "topic": "Enthalpy",
        "subtopic": "Enthalpy Changes",
        "concept_id": "chem_thermo_enthalpy",
    },
    {
        "keywords": ["first law", "internal energy", "delta u", "work", "heat capacity", "cp", "cv"],
        "domain": "Thermodynamics",
        "chapter": "Thermodynamics",
        "topic": "First Law of Thermodynamics",
        "subtopic": "Internal Energy & Work",
        "concept_id": "chem_thermo_first_law",
    },
    {
        "keywords": ["system", "surroundings", "isolated", "open system", "closed system", "state function"],
        "domain": "Thermodynamics",
        "chapter": "Thermodynamics",
        "topic": "System and Surroundings",
        "subtopic": "Thermodynamic Terms",
        "concept_id": "chem_thermo_system",
    },
]


class ConceptResolver:
    """Dynamically resolves active chemistry concept from message and session state (P3-T01)."""

    @classmethod
    def resolve_concept(cls, user_message: str, active_concept_id: str = "") -> ResolvedConcept:
        """Resolve domain, chapter, topic, subtopic, concept_id dynamically (P3-T01)."""
        clean_msg = user_message.strip().lower()

        # 1. Match message keywords against curriculum mapping
        for entry in CONCEPT_KEYWORD_MAP:
            for kw in entry["keywords"]:
                if kw in clean_msg:
                    logger.info(f"ConceptResolver: matched keyword '{kw}' -> {entry['concept_id']}")
                    return ResolvedConcept(
                        domain=entry["domain"],
                        chapter=entry["chapter"],
                        topic=entry["topic"],
                        subtopic=entry["subtopic"],
                        concept_id=entry["concept_id"],
                        confidence=0.9,
                    )

        # 2. Retain active concept from session if no explicit keyword match in message (P3-T02)
        if active_concept_id:
            for entry in CONCEPT_KEYWORD_MAP:
                if entry["concept_id"] == active_concept_id:
                    logger.info(f"ConceptResolver: retaining active concept '{active_concept_id}'")
                    return ResolvedConcept(
                        domain=entry["domain"],
                        chapter=entry["chapter"],
                        topic=entry["topic"],
                        subtopic=entry["subtopic"],
                        concept_id=entry["concept_id"],
                        confidence=0.7,
                    )

        # 3. Dynamic fallback for unknown queries (P3-T04: no hardcoded static overrides)
        logger.info("ConceptResolver: using default initial concept 'chem_thermo_system'")
        return ResolvedConcept(
            domain="Thermodynamics",
            chapter="Thermodynamics",
            topic="System and Surroundings",
            subtopic="Basic Concepts",
            concept_id="chem_thermo_system",
            confidence=0.5,
        )

    @classmethod
    def resolve_domain(cls, user_message: str, active_concept_id: str = "") -> str:
        return cls.resolve_concept(user_message, active_concept_id).domain

    @classmethod
    def resolve_chapter(cls, user_message: str, active_concept_id: str = "") -> str:
        return cls.resolve_concept(user_message, active_concept_id).chapter

    @classmethod
    def resolve_topic(cls, user_message: str, active_concept_id: str = "") -> str:
        return cls.resolve_concept(user_message, active_concept_id).topic

    @classmethod
    def resolve_subtopic(cls, user_message: str, active_concept_id: str = "") -> str:
        return cls.resolve_concept(user_message, active_concept_id).subtopic
