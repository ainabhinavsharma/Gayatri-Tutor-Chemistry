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


def build_student_dashboard_payload(student_id: str = "demo_student_001") -> dict:
    """Build a comprehensive, student-centric dashboard payload for the UI.

    Translates raw mastery scores, prerequisite graphs, active misconceptions,
    and event telemetry into an encouraging, actionable student dashboard.
    """
    from core.tutor.adaptive import EventLogger, StudentProfile
    from core.learning.misconceptions import REMEDIATION_GUIDANCE, ALL_MISCONCEPTIONS
    from datetime import datetime

    student = StudentProfile.load_from_file()
    event_logger = EventLogger()
    events = event_logger.get_recent_events(student_id=student.student_id, limit=20)

    # 1. NCERT Core Chapters Definitions
    chapters_def = [
        {
            "id": "thermodynamics",
            "unit": "Unit 6",
            "title": "Chemical Thermodynamics",
            "color": "#e94560",
            "concepts": [
                "THERMO_SYSTEM", "THERMO_HEAT", "THERMO_WORK",
                "THERMO_INTERNAL_ENERGY", "THERMO_SIGN_CONVENTION",
                "THERMO_FIRST_LAW", "THERMO_ENTHALPY"
            ],
            "action_text": "Resume Chapter →",
            "target_concept": "THERMO_FIRST_LAW",
            "prompt": "Can you explain the First Law of Thermodynamics and how work and heat are related?",
        },
        {
            "id": "bonding",
            "unit": "Unit 4",
            "title": "Chemical Bonding & VSEPR",
            "color": "#53a8b6",
            "concepts": [
                "BOND_LEWIS", "BOND_LONE_PAIRS", "BOND_VSEPR",
                "BOND_GEOMETRY", "BOND_HYBRIDISATION"
            ],
            "action_text": "Practice Geometry →",
            "target_concept": "BOND_GEOMETRY",
            "prompt": "Why does NH3 have a trigonal pyramidal shape instead of tetrahedral or trigonal planar?",
        },
        {
            "id": "periodicity",
            "unit": "Unit 3",
            "title": "Classification & Periodic Trends",
            "color": "#9b59b6",
            "concepts": [
                "PERIOD_ATOMIC_RADIUS", "PERIOD_IONIC_RADIUS",
                "PERIOD_IONISATION_ENERGY", "PERIOD_ELECTRON_AFFINITY",
                "PERIOD_ELECTRONEGATIVITY", "PERIOD_TRENDS_OVERVIEW"
            ],
            "action_text": "Review Trends →",
            "target_concept": "PERIOD_IONIC_RADIUS",
            "prompt": "How does ionic radius change across isoelectronic species like N3-, O2-, F-, and Na+?",
        },
        {
            "id": "coordination",
            "unit": "Unit 9",
            "title": "Coordination Compounds",
            "color": "#f39c12",
            "concepts": [
                "COORD_ENTITY", "COORD_LIGAND", "COORD_NUMBER",
                "COORD_OXIDATION_STATE", "COORD_NOMENCLATURE", "COORD_GEOMETRY"
            ],
            "action_text": "Start Nomenclature →",
            "target_concept": "COORD_LIGAND",
            "prompt": "What is the difference between a monodentate, bidentate, and ambidentate ligand?",
        },
    ]

    all_concept_scores: List[float] = []
    total_mastered = 0
    total_practicing = 0
    chapter_cards = []

    for ch in chapters_def:
        c_scores = [student.get_mastery(cid, 0.40) for cid in ch["concepts"]]
        all_concept_scores.extend(c_scores)

        mastered = sum(1 for s in c_scores if s >= 0.70)
        practicing = sum(1 for s in c_scores if 0.30 <= s < 0.70)
        exploring = sum(1 for s in c_scores if s < 0.30)
        avg_score = round(sum(c_scores) / len(c_scores), 2) if c_scores else 0.40
        avg_pct = int(avg_score * 100)

        total_mastered += mastered
        total_practicing += practicing

        if avg_pct >= 80:
            status_label = f"{avg_pct}% Advanced"
        elif avg_pct >= 60:
            status_label = f"{avg_pct}% Proficient"
        else:
            status_label = f"{avg_pct}% Foundation"

        parts = []
        if mastered > 0:
            parts.append(f"{mastered} Mastered")
        if practicing > 0:
            parts.append(f"{practicing} Practicing")
        if exploring > 0:
            parts.append(f"{exploring} Exploring")
        status_sub = " • ".join(parts) if parts else "Ready to begin"

        chapter_cards.append({
            "id": ch["id"],
            "unit": ch["unit"],
            "title": ch["title"],
            "color": ch["color"],
            "mastery_pct": avg_pct,
            "status_label": status_label,
            "status_sub": status_sub,
            "action_text": ch["action_text"],
            "target_concept": ch["target_concept"],
            "prompt": ch["prompt"],
        })

    total_concepts = len(all_concept_scores) if all_concept_scores else 24
    overall_mastery_pct = int((sum(all_concept_scores) / len(all_concept_scores)) * 100) if all_concept_scores else 64

    # 2. Roadmap DAG Nodes (for current topic: Thermodynamics)
    roadmap_nodes_def = [
        {
            "id": "THERMO_SYSTEM",
            "name": "System & Surroundings",
            "desc": "Open, closed, isolated systems",
        },
        {
            "id": "THERMO_HEAT",
            "name": "Heat & Work",
            "desc": "Energy transfer pathways (q, w)",
        },
        {
            "id": "THERMO_INTERNAL_ENERGY",
            "name": "Internal Energy (U)",
            "desc": "Microscopic kinetic & potential energy",
        },
        {
            "id": "THERMO_FIRST_LAW",
            "name": "First Law (ΔU = q + w)",
            "desc": "IUPAC sign conventions",
        },
        {
            "id": "THERMO_ENTHALPY",
            "name": "Enthalpy (ΔH)",
            "desc": "Heat transfer at constant pressure",
        },
    ]

    curr_cid = student.current_concept
    roadmap_nodes = []
    for node in roadmap_nodes_def:
        cid = node["id"]
        score = student.get_mastery(cid, 0.40)
        pct = int(score * 100)

        if cid == curr_cid:
            status = "focus"
            status_text = f"🎯 {pct}% Focus"
            badge_icon = "●"
        elif score >= 0.70:
            status = "mastered"
            status_text = f"✓ {pct}% Mastered"
            badge_icon = "🔓"
        elif score >= 0.30:
            status = "practicing"
            status_text = f"{pct}% Practicing"
            badge_icon = "🔓"
        else:
            status = "locked"
            status_text = f"{pct}% Exploring"
            badge_icon = "🔒"

        roadmap_nodes.append({
            "id": cid,
            "name": node["name"],
            "desc": node["desc"],
            "mastery_pct": pct,
            "status": status,
            "status_text": status_text,
            "badge_icon": badge_icon,
        })

    # 3. Smart Focus Area (Pedagogical Misconception Tip)
    if student.misconceptions:
        active_misc = student.misconceptions[0]
        focus_topic = "Chemical Thermodynamics"
        focus_title = "Focus Area: Active Misconception"
        if "SIGN_CONVENTION" in active_misc or "EXPANSION_WORK" in active_misc:
            focus_tip = (
                "In gas expansion against external pressure, the system does work on the surroundings. "
                "Energy leaves the system, so work is negative (w < 0)."
            )
            practice_prompt = "A gas expands from 2.0 L to 5.0 L against 1.0 atm external pressure while absorbing 400 J of heat. What is delta U?"
        elif active_misc in REMEDIATION_GUIDANCE:
            focus_tip = REMEDIATION_GUIDANCE[active_misc]
            practice_prompt = f"Can we review the key distinction for {active_misc.replace('_', ' ').lower()}?"
        else:
            focus_tip = "Remember that state functions depend only on initial and final states, while heat (q) and work (w) depend on the exact pathway taken."
            practice_prompt = "Can you give me a question testing whether heat and work are state functions or path functions?"
    else:
        active_misc = None
        focus_topic = "Chemical Thermodynamics"
        focus_title = "Ready to Begin"
        focus_tip = "Start with the First Law of Thermodynamics to explore energy conservation, heat transfer, and expansion work."
        practice_prompt = "Please explain the First Law of Thermodynamics and how work and heat are related."

    # 4. Spaced Review Due
    if student.mastery:
        spaced_review = {
            "title": "Thermodynamics Review",
            "due_label": "Recommended",
            "description": "Reinforce concepts you've practiced to lock them into long-term memory!",
            "prompt": "Let's do a quick check on the concepts we just discussed.",
        }
    else:
        spaced_review = {
            "title": "Welcome to Chemistry",
            "due_label": "Getting Started",
            "description": "Begin by asking a question on Thermodynamics, Bonding, or Periodic Trends.",
            "prompt": "Can you explain the First Law of Thermodynamics?",
        }

    # 5. Humanized Learning Journey Stream
    humanized_stream = []
    for ev in reversed(events):
        etype = ev.get("event")
        ts = ev.get("timestamp", "")
        # Format time display (HH:MM)
        time_str = "--:--"
        if "T" in ts:
            try:
                time_str = ts.split("T")[1][:5]
            except Exception:
                time_str = ts[:5]

        cid = ev.get("concept_id", "")
        concept_clean = cid.replace("THERMO_", "").replace("BOND_", "").replace("PERIOD_", "").replace("COORD_", "").replace("_", " ").title()

        if etype == "ANSWER_EVALUATED":
            res = ev.get("result", "")
            if res == "CORRECT":
                delta = ev.get("mastery_delta", 0.05)
                new_m = ev.get("new_mastery", 0.7)
                old_m = ev.get("previous_mastery", new_m - delta)
                humanized_stream.append({
                    "icon": "✓",
                    "color": "#27c93f",
                    "title": f"Correct Answer on {concept_clean or 'Concept'}",
                    "time": time_str,
                    "description": "Demonstrated solid understanding and accurate reasoning.",
                    "badge": f"+{int(delta * 100)}% Mastery Boost ({int(old_m * 100)}% → {int(new_m * 100)}%)",
                })
            else:
                humanized_stream.append({
                    "icon": "⚠️",
                    "color": "#e94560",
                    "title": f"Practicing {concept_clean or 'Concept'}",
                    "time": time_str,
                    "description": "Identified conceptual opportunity to refine sign conventions without penalty.",
                    "badge": None,
                })
        elif etype == "HINT_GIVEN":
            lvl = ev.get("hint_level", 1)
            humanized_stream.append({
                "icon": "💡",
                "color": "#53a8b6",
                "title": f"Unlocked Hint Level {lvl}",
                "time": time_str,
                "description": f"Socratic guidance provided to help uncover the answer independently.",
                "badge": None,
            })
        elif etype == "REMEDIATION_STARTED":
            prereq = ev.get("prerequisite_concept", "Prerequisite").replace("THERMO_", "").replace("_", " ").title()
            humanized_stream.append({
                "icon": "🔄",
                "color": "#f5c542",
                "title": f"Reinforced Prerequisite: {prereq}",
                "time": time_str,
                "description": f"Strengthened foundational concepts before progressing to advanced applications.",
                "badge": None,
            })
        elif etype == "EXPLANATION_GENERATED":
            humanized_stream.append({
                "icon": "📖",
                "color": "#9b59b6",
                "title": f"Explored {concept_clean or 'Chemistry Concepts'}",
                "time": time_str,
                "description": "Engaged with guided Socratic explanation and everyday analogy.",
                "badge": None,
            })
        elif etype == "SESSION_STARTED":
            humanized_stream.append({
                "icon": "🚀",
                "color": "#53a8b6",
                "title": "Learning Session Ready",
                "time": time_str,
                "description": "NCERT senior secondary chemistry adaptive tutor initialized.",
                "badge": None,
            })

        if len(humanized_stream) >= 5:
            break

    # Default fallback events if event log is sparse
    # Clean fallback event if event log is empty
    if not humanized_stream:
        humanized_stream = [
            {
                "icon": "✨",
                "color": "#53a8b6",
                "title": "Welcome to Gayatri Chemistry Tutor",
                "time": "Just now",
                "description": "Start asking questions or practicing problems to build your personalized mastery roadmap!",
                "badge": "Ready to Start",
            }
        ]

    student_display_name = student.name if student.name and student.name != "Demo Student" else "Student"
    return {
        "ok": True,
        "student": {
            "name": student_display_name,
            "initials": "".join([part[0].upper() for part in student_display_name.split()][:2]) or "ST",
            "level": "Class 11 CBSE Chemistry",
            "target": "NCERT Foundation & Senior Secondary Mastery • Local Offline Learning",
            "overall_mastery": overall_mastery_pct,
            "mastered_count": total_mastered,
            "total_concepts": total_concepts,
            "streak_days": 1,
        },
        "chapters": chapter_cards,
        "roadmap": {
            "topic_title": "Thermodynamics",
            "topic_subtitle": "Sequential prerequisite DAG showing your path through energy concepts",
            "nodes": roadmap_nodes,
        },
        "focus_area": {
            "topic": focus_topic,
            "title": focus_title,
            "tip": focus_tip,
            "concept_id": active_misc,
            "prompt": practice_prompt,
        },
        "spaced_review": spaced_review,
        "activity_stream": humanized_stream,
    }

