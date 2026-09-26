"""Progress and Analytics Service (Phase 9).

Single authoritative ProgressService API reading directly from persisted evidence & learning state:
persisted events -> learning engine -> progress service -> UI
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.learning.misconceptions import MisconceptionTracker
from core.learning.scheduler import SpacedReviewScheduler
from core.security.validation import validate_concept_id, validate_student_id

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


# Controlled concept domain mapping
CONCEPT_DOMAINS: dict[str, str] = {
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
    "chem_equil_dynamic": "Physical Chemistry",
    "chem_equil_constants": "Physical Chemistry",
    "chem_equil_le_chatelier": "Physical Chemistry",
    "chem_equil_ionic": "Physical Chemistry",
    "chem_coord_entities": "Inorganic Chemistry",
    "chem_coord_werner": "Inorganic Chemistry",
    "chem_coord_nomenclature": "Inorganic Chemistry",
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

    def __init__(self, state_manager: TutorStateManager | None = None):
        self.state_manager = state_manager
        self.scheduler = SpacedReviewScheduler()

    def get_concept_progress(
        self,
        student_id: str,
        concept_id: str,
        state_manager: TutorStateManager | None = None,
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
        state_manager: TutorStateManager | None = None,
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
        domain_totals: dict[str, list[float]] = {
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

    def get_student_progress(
        self,
        student_id: str,
        state_manager: TutorStateManager | None = None,
    ) -> dict:
        """GET /student/progress - Overall mastery, concepts learned, questions attempted/correct, accuracy."""
        student_id = validate_student_id(student_id)
        summary = self.get_student_progress_summary(student_id, state_manager)
        concepts = summary["concepts"]

        attempts = sum(c["exposure_count"] for c in concepts)
        corrects = sum(c["correct_count"] for c in concepts)
        accuracy = round(corrects / attempts, 4) if attempts > 0 else 0.0
        mastered_count = sum(1 for c in concepts if c["mastery"] >= 0.70)

        return {
            "ok": True,
            "student_id": student_id,
            "overall_mastery": summary["overall_mastery"],
            "overall_mastery_pct": int(summary["overall_mastery"] * 100),
            "concepts_learned": mastered_count,
            "total_concepts": len(concepts),
            "questions_attempted": attempts,
            "questions_correct": corrects,
            "accuracy": accuracy,
            "accuracy_pct": round(accuracy * 100, 1),
            "domain_breakdown": summary["domain_mastery"],
            "reviews_due_count": summary["reviews_due_count"],
            "active_misconceptions_count": summary["active_misconceptions_count"],
        }

    def get_recent_sessions(
        self,
        student_id: str,
        limit: int = 10,
        state_manager: TutorStateManager | None = None,
    ) -> dict:
        """GET /student/recent-sessions - History of recent tutoring sessions."""
        student_id = validate_student_id(student_id)
        from core.tutor.adaptive import EventLogger
        logger = EventLogger()
        events = logger.get_recent_events(student_id=student_id, limit=limit * 5)

        sessions_map: dict[str, dict] = {}
        for ev in events:
            sid = ev.get("session_id", "default_session")
            if sid not in sessions_map:
                sessions_map[sid] = {
                    "session_id": sid,
                    "date": ev.get("timestamp", "")[:10],
                    "topic": get_concept_domain(ev.get("concept_id", "")),
                    "questions_attempted": 0,
                    "questions_correct": 0,
                    "concepts_practiced": set(),
                    "misconceptions_detected": set(),
                }
            s = sessions_map[sid]
            cid = ev.get("concept_id")
            if cid:
                s["concepts_practiced"].add(cid)
            if ev.get("event") == "ANSWER_EVALUATED":
                s["questions_attempted"] += 1
                if ev.get("result") == "CORRECT":
                    s["questions_correct"] += 1
            if ev.get("event") == "MISCONCEPTION_DETECTED" or ev.get("misconception_code"):
                code = ev.get("misconception_code") or ev.get("details", {}).get("code")
                if code:
                    s["misconceptions_detected"].add(code)

        result_sessions = []
        for s in list(sessions_map.values())[-limit:]:
            att = s["questions_attempted"]
            corr = s["questions_correct"]
            acc = round(corr / att, 4) if att > 0 else 0.0
            result_sessions.append({
                "session_id": s["session_id"],
                "date": s["date"],
                "topic": s["topic"],
                "questions_attempted": att,
                "questions_correct": corr,
                "accuracy": acc,
                "concepts_practiced": list(s["concepts_practiced"]),
                "misconceptions_detected": list(s["misconceptions_detected"]),
            })

        return {"ok": True, "student_id": student_id, "sessions": result_sessions}

    def get_activity_feed(
        self,
        student_id: str,
        limit: int = 20,
    ) -> dict:
        """GET /student/activity - Event stream of student achievements."""
        student_id = validate_student_id(student_id)
        from core.tutor.adaptive import EventLogger
        logger = EventLogger()
        events = logger.get_recent_events(student_id=student_id, limit=limit)
        return {"ok": True, "student_id": student_id, "activity": events}

    def get_concept_heatmap(
        self,
        student_id: str,
        state_manager: TutorStateManager | None = None,
    ) -> dict:
        """GET /student/concepts - Categorized concepts (mastered, developing, weak, not_started, needs_review)."""
        student_id = validate_student_id(student_id)
        summary = self.get_student_progress_summary(student_id, state_manager)
        heatmap: dict[str, list[dict]] = {
            "mastered": [],
            "developing": [],
            "weak": [],
            "not_started": [],
            "needs_review": [],
        }

        for c in summary["concepts"]:
            m = c["mastery"]
            exp = c["exposure_count"]
            due = c["is_review_due"]

            cat = "not_started"
            if due and exp > 0:
                cat = "needs_review"
            elif exp == 0:
                cat = "not_started"
            elif m >= 0.70:
                cat = "mastered"
            elif m >= 0.40:
                cat = "developing"
            else:
                cat = "weak"

            heatmap[cat].append({
                "concept_id": c["concept_id"],
                "domain": c["domain"],
                "mastery": m,
                "status": c["status"],
                "active_misconceptions": c["active_misconceptions"],
            })

        return {"ok": True, "student_id": student_id, "heatmap": heatmap}

    def get_recommended_actions(
        self,
        student_id: str,
        state_manager: TutorStateManager | None = None,
    ) -> dict:
        """GET /student/recommendations - Application policy engine next learning actions."""
        student_id = validate_student_id(student_id)
        summary = self.get_student_progress_summary(student_id, state_manager)
        recommendations = []

        # Rule 1: Spaced reviews due
        due_concepts = [c for c in summary["concepts"] if c["is_review_due"]]
        if due_concepts:
            target = due_concepts[0]
            recommendations.append({
                "priority": 1,
                "type": "REVIEW_DUE",
                "concept_id": target["concept_id"],
                "title": f"Review {target['concept_id']}",
                "reason": "Concept is due for spaced review retention check",
            })

        # Rule 2: Misconception remediation
        misc_concepts = [c for c in summary["concepts"] if c["active_misconceptions"]]
        if misc_concepts:
            target = misc_concepts[0]
            code = target["active_misconceptions"][0]
            recommendations.append({
                "priority": 2,
                "type": "REMEDIATION",
                "concept_id": target["concept_id"],
                "misconception_code": code,
                "title": f"Address {code} in {target['concept_id']}",
                "reason": f"Active misconception detected: {code}",
            })

        # Rule 3: Weak / Developing concepts practice
        weak_concepts = [c for c in summary["concepts"] if 0.0 < c["mastery"] < 0.70]
        if weak_concepts:
            target = weak_concepts[0]
            recommendations.append({
                "priority": 3,
                "type": "PRACTICE",
                "concept_id": target["concept_id"],
                "title": f"Practice {target['concept_id']}",
                "reason": f"Current mastery ({target['mastery']:.0%}) is below mastery threshold (70%)",
            })

        # Fallback default
        if not recommendations:
            recommendations.append({
                "priority": 4,
                "type": "EXPLORE_NEW",
                "concept_id": "THERMO_FIRST_LAW",
                "title": "Explore Chemical Thermodynamics",
                "reason": "Ready to begin foundational senior secondary chemistry concepts",
            })

        return {"ok": True, "student_id": student_id, "recommendations": recommendations}

    def get_session_summary(
        self,
        student_id: str,
        session_id: str | None = None,
        state_manager: TutorStateManager | None = None,
    ) -> dict:
        """GET /student/session-summary - End-of-session recap stats."""
        student_id = validate_student_id(student_id)
        sessions_res = self.get_recent_sessions(student_id, limit=5, state_manager=state_manager)
        sessions = sessions_res.get("sessions", [])

        target_session = None
        if session_id:
            for s in sessions:
                if s["session_id"] == session_id:
                    target_session = s
                    break

        if not target_session and sessions:
            target_session = sessions[-1]

        if not target_session:
            return {
                "ok": True,
                "student_id": student_id,
                "session_summary": {
                    "session_id": session_id or "new_session",
                    "questions_attempted": 0,
                    "questions_correct": 0,
                    "accuracy": 0.0,
                    "concepts_practiced": [],
                    "newly_strengthened": [],
                    "needs_review": [],
                    "next_recommended_session": "Chemical Thermodynamics",
                }
            }

        return {
            "ok": True,
            "student_id": student_id,
            "session_summary": {
                "session_id": target_session["session_id"],
                "questions_attempted": target_session["questions_attempted"],
                "questions_correct": target_session["questions_correct"],
                "accuracy": target_session["accuracy"],
                "concepts_practiced": target_session["concepts_practiced"],
                "newly_strengthened": target_session["concepts_practiced"][:2],
                "needs_review": target_session["misconceptions_detected"],
                "next_recommended_session": "Gibbs Free Energy application",
            }
        }



def build_student_dashboard_payload(student_id: str = "demo_student_001") -> dict:
    """Build a comprehensive, student-centric dashboard payload for the UI.

    Translates raw mastery scores, prerequisite graphs, active misconceptions,
    and event telemetry into an encouraging, actionable student dashboard.
    """
    from core.learning.misconceptions import REMEDIATION_GUIDANCE
    from core.tutor.adaptive import EventLogger, StudentProfile

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

    all_concept_scores: list[float] = []
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
                "description": "Socratic guidance provided to help uncover the answer independently.",
                "badge": None,
            })
        elif etype == "REMEDIATION_STARTED":
            prereq = ev.get("prerequisite_concept", "Prerequisite").replace("THERMO_", "").replace("_", " ").title()
            humanized_stream.append({
                "icon": "🔄",
                "color": "#f5c542",
                "title": f"Reinforced Prerequisite: {prereq}",
                "time": time_str,
                "description": "Strengthened foundational concepts before progressing to advanced applications.",
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

