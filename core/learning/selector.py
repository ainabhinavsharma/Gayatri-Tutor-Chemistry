"""Concept Selector Engine (P4-T04).

Ranks candidate learning concepts for a student using multi-factor adaptive scoring:
score = prerequisite_readiness * mastery_gap * review_urgency * curriculum_importance * misconception_risk
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


@dataclass
class ConceptSelectionResult:
    selected_concept_id: str
    score: float
    breakdown: dict
    candidate_rankings: list[dict]


DEFAULT_PREREQUISITES_MAP: dict[str, list[str]] = {
    # NCERT standard curriculum IDs
    'chem_thermo_first_law': ['chem_thermo_system'],
    'chem_thermo_enthalpy': ['chem_thermo_first_law'],
    'chem_thermo_hess': ['chem_thermo_enthalpy'],
    'chem_thermo_heat_cap': ['chem_thermo_first_law'],
    'chem_thermo_entropy': ['chem_thermo_enthalpy'],
    'chem_thermo_gibbs': ['chem_thermo_entropy', 'chem_thermo_enthalpy'],
    'chem_thermo_calorimetry': ['chem_thermo_heat_cap'],
    'chem_thermo_formation': ['chem_thermo_hess'],
    'chem_inorg_bonding': ['chem_inorg_periodic'],
    'chem_inorg_sblock': ['chem_inorg_periodic', 'chem_inorg_bonding'],
    'chem_inorg_pblock': ['chem_inorg_periodic', 'chem_inorg_bonding'],
    'chem_balancing': ['chem_inorg_periodic'],
    'chem_stoichiometry': ['chem_balancing'],
    # Dot-notation backward compatibility
    'thermo.hess_law': ['thermo.enthalpy', 'thermo.first_law'],
    'thermo.gibbs': ['thermo.enthalpy', 'thermo.entropy'],
    'inorganic.periodicity': ['inorganic.atomic_structure'],
    'inorganic.coordination': ['inorganic.periodicity', 'inorganic.bonding'],
}


class ConceptSelector:
    """Evidence-driven concept selector for adaptive lesson/practice sequencing."""

    def __init__(
        self,
        prerequisite_threshold: float = 0.7,
        prerequisites_map: dict[str, list[str]] | None = None,
    ):
        self.prerequisite_threshold = prerequisite_threshold
        # Default prerequisite map for Thermodynamics & Inorganic (NCERT + legacy)
        self.prerequisites_map = prerequisites_map or DEFAULT_PREREQUISITES_MAP

    def evaluate_concept_score(
        self,
        student_id: str,
        concept_id: str,
        state_manager: TutorStateManager,
    ) -> dict:
        """Calculate ranking score and factor breakdown for a single concept."""
        mastery_record = state_manager.get_student_concept_mastery(student_id, concept_id)
        current_mastery = mastery_record.mastery

        # 1. Prerequisite readiness
        prereqs = self.prerequisites_map.get(concept_id, [])
        if not prereqs:
            prereq_readiness = 1.0
        else:
            ready_count = 0
            for p_id in prereqs:
                p_mastery = state_manager.get_student_concept_mastery(student_id, p_id).mastery
                if p_mastery >= self.prerequisite_threshold:
                    ready_count += 1
            prereq_readiness = 1.0 if ready_count == len(prereqs) else 0.2

        # 2. Mastery gap (focus on concepts needing improvement)
        mastery_gap = max(0.05, 1.0 - current_mastery)

        # 3. Review urgency
        next_review = mastery_record.next_review_at
        if next_review:
            try:
                due_dt = datetime.fromisoformat(next_review)
                review_urgency = 2.0 if datetime.now() >= due_dt else 1.0
            except ValueError:
                review_urgency = 1.0
        else:
            review_urgency = 1.0

        # 4. Curriculum importance
        curriculum_importance = 1.0

        # 5. Misconception risk (boost score if active unresolved misconceptions exist)
        has_misconception = False
        try:
            cursor = state_manager.conn.execute(
                'SELECT 1 FROM student_misconceptions WHERE student_id = ? AND concept_id = ? AND resolved = 0',
                (student_id, concept_id)
            )
            has_misconception = bool(cursor.fetchone())
        except Exception:
            has_misconception = False

        misconception_risk = 1.5 if has_misconception else 1.0

        # Total score
        total_score = round(
            prereq_readiness * mastery_gap * review_urgency * curriculum_importance * misconception_risk, 4
        )

        return {
            'concept_id': concept_id,
            'total_score': total_score,
            'current_mastery': current_mastery,
            'prereq_readiness': prereq_readiness,
            'mastery_gap': mastery_gap,
            'review_urgency': review_urgency,
            'curriculum_importance': curriculum_importance,
            'misconception_risk': misconception_risk,
        }

    def select_next_concept(
        self,
        student_id: str,
        candidate_concept_ids: list[str],
        state_manager: TutorStateManager,
    ) -> ConceptSelectionResult:
        """Select the highest-ranked candidate concept for the student."""
        if not candidate_concept_ids:
            raise ValueError("candidate_concept_ids list cannot be empty.")

        rankings = []
        for cid in candidate_concept_ids:
            breakdown = self.evaluate_concept_score(student_id, cid, state_manager)
            rankings.append(breakdown)

        # Sort by total_score descending
        rankings.sort(key=lambda r: r['total_score'], reverse=True)
        top = rankings[0]

        return ConceptSelectionResult(
            selected_concept_id=top['concept_id'],
            score=top['total_score'],
            breakdown=top,
            candidate_rankings=rankings,
        )
