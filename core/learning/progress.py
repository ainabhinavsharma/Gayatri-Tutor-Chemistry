"""Progress and Analytics Service (Phase 9).

Single authoritative ProgressService API reading directly from persisted evidence & learning state:
persisted events -> learning engine -> progress service -> UI
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from core.learning.misconceptions import MisconceptionTracker
from core.learning.scheduler import SpacedReviewScheduler
from core.security.validation import validate_concept_id, validate_student_id

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


# Controlled concept domain mapping
CONCEPT_DOMAINS: Dict[str, str] = {
    # Legacy / test dot-notation mappings
    "thermo.enthalpy": "Thermodynamics",
    "thermo.first_law": "Thermodynamics",
    "thermo.hess_law": "Thermodynamics",
    "thermo.gibbs": "Thermodynamics",
    "thermo.entropy": "Thermodynamics",
    "thermo.work": "Thermodynamics",
    "inorganic.atomic_structure": "Inorganic Chemistry",
    "inorganic.periodicity": "Inorganic Chemistry",
    "inorganic.coordination": "Inorganic Chemistry",
    "inorganic.redox": "Inorganic Chemistry",
    "inorganic.bonding": "Inorganic Chemistry",
    # Canonical NCERT Chemistry curriculum concepts
    "chem_thermo_system_surroundings": "Thermodynamics",
    "chem_thermo_first_law": "Thermodynamics",
    "chem_thermo_enthalpy": "Thermodynamics",
    "chem_thermo_hess_law": "Thermodynamics",
    "chem_thermo_entropy": "Thermodynamics",
    "chem_thermo_gibbs": "Thermodynamics",
    "chem_inorg_periodic_trends": "Inorganic Chemistry",
    "chem_inorg_electronic": "Inorganic Chemistry",
    "chem_inorg_bonding_lewis": "Inorganic Chemistry",
    "chem_inorg_vsepr": "Inorganic Chemistry",
    "chem_inorg_hybridization": "Inorganic Chemistry",
    "chem_inorg_redox_intro": "Inorganic Chemistry",
    "chem_inorg_balancing": "Inorganic Chemistry",
    "chem_balancing": "Inorganic Chemistry",
    "chem_inorg_periodic": "Inorganic Chemistry",
    "chem_inorg_bonding": "Inorganic Chemistry",
    "chem_inorg_sblock": "Inorganic Chemistry",
    "chem_inorg_pblock": "Inorganic Chemistry",
    "chem_thermo_system": "Thermodynamics",
    "chem_thermo_hess": "Thermodynamics",
    "chem_thermo_heat_cap": "Thermodynamics",
    "chem_thermo_calorimetry": "Thermodynamics",
    "chem_thermo_formation": "Thermodynamics",
    "chem_stoichiometry": "Stoichiometry & Physical",
    "chem_stoichiometry_mole": "Stoichiometry & Physical",
    "chem_stoichiometry_limiting": "Stoichiometry & Physical",
}


def get_concept_domain(concept_id: str) -> str:
    """Resolve domain for a concept ID with prefix fallback."""
    if concept_id in CONCEPT_DOMAINS:
        return CONCEPT_DOMAINS[concept_id]
    cid = concept_id.lower()
    if "thermo" in cid:
        return "Thermodynamics"
    if "inorg" in cid or "periodic" in cid or "bond" in cid or "balance" in cid:
        return "Inorganic Chemistry"
    if "stoich" in cid or "mole" in cid:
        return "Stoichiometry & Physical"
    if "organic" in cid:
        return "Organic Chemistry"
    return "General Chemistry"



def get_status_label(mastery: float, exposure_count: int, is_due: bool) -> str:
    """Compute standard progress status label (P9-T03)."""
    if is_due and exposure_count > 0:
        return "REVIEW_DUE"
    if exposure_count == 0:
        return "NEW"
    if exposure_count < 3:
        return "LEARNING"
    if mastery >= 0.85:
        return "MASTERED"
    if mastery >= 0.70:
        return "PROFICIENT"
    return "PRACTICING"


class ProgressService:
    """Authoritative progress service for student analytics and UI consumption."""

    def __init__(self, state_manager: Optional[TutorStateManager] = None):
        self.state_manager = state_manager
        self.scheduler = SpacedReviewScheduler()

    def get_concept_progress(
        self,
        student_id: str,
        concept_id: str,
        state_manager: Optional[TutorStateManager] = None,
    ) -> dict:
        """Get detailed progress for a single concept."""
        student_id = validate_student_id(student_id)
        concept_id = validate_concept_id(concept_id)
        sm = state_manager or self.state_manager
        if not sm:
            raise ValueError("State manager is required.")

        rec = sm.get_student_concept_mastery(student_id, concept_id)
        tracker = MisconceptionTracker(sm)
        active_misconceptions = [m.misconception_code for m in tracker.get_active_misconceptions(student_id, concept_id)]

        is_due = self.scheduler.is_review_due(rec.next_review_at)
        total_attempts = rec.exposure_count
        accuracy = round(rec.correct_count / total_attempts, 4) if total_attempts > 0 else 0.0
        status = get_status_label(rec.mastery, total_attempts, is_due)
        domain = get_concept_domain(concept_id)

        return {
            "student_id": student_id,
            "concept_id": concept_id,
            "domain": domain,
            "mastery": rec.mastery,
            "confidence": rec.confidence,
            "status": status,
            "exposure_count": total_attempts,
            "correct_count": rec.correct_count,
            "error_count": rec.error_count,
            "accuracy": accuracy,
            "difficulty_level": rec.difficulty_level,
            "next_review_at": rec.next_review_at,
            "is_review_due": is_due,
            "active_misconceptions": active_misconceptions,
        }

    def get_student_progress_summary(
        self,
        student_id: str,
        state_manager: Optional[TutorStateManager] = None,
    ) -> dict:
        """Get comprehensive overall, domain-level, and concept-level student progress."""
        student_id = validate_student_id(student_id)
        sm = state_manager or self.state_manager
        if not sm:
            raise ValueError("State manager is required.")

        cursor = sm.conn.execute(
            "SELECT DISTINCT concept_id FROM student_concept_mastery WHERE student_id = ?",
            (student_id,)
        )
        concept_ids = [row["concept_id"] for row in cursor.fetchall()]

        if not concept_ids:
            # Fallback to standard curriculum concept list if no mastery rows exist yet
            concept_ids = list(CONCEPT_DOMAINS.keys())

        concepts_progress = [self.get_concept_progress(student_id, cid, sm) for cid in concept_ids]

        # Domain breakdown
        domain_totals: Dict[str, List[float]] = {
            "Thermodynamics": [],
            "Inorganic Chemistry": [],
        }

        reviews_due_count = 0
        active_misconceptions_count = 0

        for p in concepts_progress:
            d = p["domain"]
            if d not in domain_totals:
                domain_totals[d] = []
            domain_totals[d].append(p["mastery"])

            if p["is_review_due"]:
                reviews_due_count += 1
            active_misconceptions_count += len(p["active_misconceptions"])

        all_masteries = [p["mastery"] for p in concepts_progress]
        overall_mastery = round(sum(all_masteries) / len(all_masteries), 4) if all_masteries else 0.0

        domain_mastery = {}
        for d, scores in domain_totals.items():
            domain_mastery[d] = round(sum(scores) / len(scores), 4) if scores else 0.0

        return {
            "student_id": student_id,
            "overall_mastery": overall_mastery,
            "domain_mastery": domain_mastery,
            "total_concepts_tracked": len(concepts_progress),
            "reviews_due_count": reviews_due_count,
            "active_misconceptions_count": active_misconceptions_count,
            "concepts": concepts_progress,
        }
