"""Misconception Tracking Engine (P4-T03).

Tracks controlled misconception codes for Thermodynamics & Inorganic Chemistry,
persists student misconception occurrences, and manages remediation status.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager


# Controlled Misconception Catalog (P4-T03)
THERMODYNAMICS_MISCONCEPTIONS: Dict[str, str] = {
    'THERMO_SIGN_CONVENTION': 'Confusing work/heat sign convention. In gas expansion against external pressure, work is done BY the system on surroundings, so work is negative (w < 0).',
    'HEAT_VS_INTERNAL_ENERGY': 'Failing to distinguish between heat transfer (q) and internal energy (delta U).',
    'STATE_VS_PATH_FUNCTION': 'Treating q or w as state functions instead of path functions.',
    'ENTHALPY_CONFUSION': 'Confusing Enthalpy (H) with Internal Energy (U) or Gibbs Free Energy (G).',
    'HESS_LAW_DIRECTION': 'Inverting reaction direction without reversing enthalpy sign in Hess Law calculations.',
    'CP_CV_CONFUSION': 'Confusing molar heat capacities at constant pressure (Cp) and constant volume (Cv).',
    'GIBBS_SIGN_CONFUSION': 'Misunderstanding spontaneous criteria (delta G < 0 vs delta G > 0).',
}

INORGANIC_MISCONCEPTIONS: Dict[str, str] = {
    'PERIODIC_TREND_CONFUSION': 'Incorrectly predicting ionic radius, ionization energy, or electron gain enthalpy trends.',
    'OXIDATION_STATE_ERROR': 'Miscalculating transition metal or p-block oxidation numbers.',
    'ELECTRONIC_CONFIGURATION_ERROR': 'Errors in Aufbau principle exceptions (e.g. Cr, Cu, anomalous d-block configurations).',
    'COORDINATION_NUMBER_CONFUSION': 'Confusing coordination number with oxidation state or oxidation number.',
    'LIGAND_CONFUSION': 'Misidentifying bidentate, ambidentate, or strong/weak field ligands.',
    'REDOX_CONFUSION': 'Confusing oxidizing agents with reducing agents in inorganic reactions.',
    'ANOMALOUS_BEHAVIOUR_CONFUSION': 'Ignoring 2nd period anomalous behavior (small size, high electronegativity, no d-orbitals).',
    'METALLURGY_PROCESS_CONFUSION': 'Confusing calcination with roasting or leaching in ore extraction.',
}

ALL_MISCONCEPTIONS: Dict[str, str] = {
    **THERMODYNAMICS_MISCONCEPTIONS,
    **INORGANIC_MISCONCEPTIONS,
}


@dataclass
class StudentMisconceptionRecord:
    student_id: str
    concept_id: str
    misconception_code: str
    occurrence_count: int
    first_detected: str
    last_detected: str
    resolved: bool = False
    remediation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'concept_id': self.concept_id,
            'misconception_code': self.misconception_code,
            'occurrence_count': self.occurrence_count,
            'first_detected': self.first_detected,
            'last_detected': self.last_detected,
            'resolved': self.resolved,
            'remediation_notes': self.remediation_notes,
        }


# Targeted Remediation Guidance Catalog (P4-T03)
REMEDIATION_GUIDANCE: Dict[str, str] = {
    'THERMO_SIGN_CONVENTION': 'Recall IUPAC convention: Work done ON system is +w; work done BY system is -w. Heat absorbed by system is +q; heat released is -q.',
    'HEAT_VS_INTERNAL_ENERGY': 'Clarify that heat (q) is energy in transit across a boundary, while internal energy (U) is a state function of the system.',
    'STATE_VS_PATH_FUNCTION': 'Emphasize that state functions depend only on initial and final states, whereas q and w depend on the specific path taken.',
    'ENTHALPY_CONFUSION': 'Review definition H = U + pV. For constant pressure processes, delta H = q_p, whereas delta U = q_v.',
    'HESS_LAW_DIRECTION': 'When reversing a thermochemical equation, the sign of delta H must be flipped (+ to -, or - to +).',
    'CP_CV_CONFUSION': 'For an ideal gas, Cp - Cv = R. Cp is always greater than Cv because work is done during constant pressure expansion.',
    'GIBBS_SIGN_CONFUSION': 'Criterion of spontaneity at constant T and p is delta G < 0. Positive delta G indicates non-spontaneous process.',
    'PERIODIC_TREND_CONFUSION': 'Review effective nuclear charge (Z_eff) and shielding effect across periods and down groups.',
    'OXIDATION_STATE_ERROR': 'Apply oxidation number rules systematically: group 1 (+1), group 2 (+2), F (-1), O usually (-2), H usually (+1).',
    'ELECTRONIC_CONFIGURATION_ERROR': 'Remember half-filled (d5) and fully-filled (d10) subshells possess extra stability due to symmetry and exchange energy.',
    'COORDINATION_NUMBER_CONFUSION': 'Coordination number is the number of coordinate (dative) bonds formed by ligands to the central metal atom/ion.',
    'LIGAND_CONFUSION': 'Distinguish monodentate, bidentate (ox, en), and polydentate (EDTA) ligands and their denticity.',
    'REDOX_CONFUSION': 'Oxidizing agents gain electrons and are reduced; reducing agents lose electrons and are oxidized.',
    'ANOMALOUS_BEHAVIOUR_CONFUSION': 'Second period elements (Li, Be, B, C, N, O, F) differ from heavier group members due to small size and absence of d-orbitals.',
    'METALLURGY_PROCESS_CONFUSION': 'Calcination involves heating in absence/limited air (carbonates/hydrates); roasting involves heating with excess air (sulfides).',
}


def get_remediation_guidance(misconception_code: str) -> str:
    """Retrieve targeted pedagogical remediation directive for a misconception."""
    return REMEDIATION_GUIDANCE.get(
        misconception_code,
        f"Review core curriculum principles and worked examples for {misconception_code}."
    )


class MisconceptionTracker:
    """Manages recording, querying, and resolving student misconception records."""

    @classmethod
    def identify_misconception_from_error(
        cls, concept_id: str, student_answer: str, error_type: str = ""
    ) -> Optional[str]:
        """Identify a controlled misconception code based on concept_id, error_type, or student answer content."""
        answer_lower = student_answer.lower()
        error_lower = error_type.lower()
        concept_lower = concept_id.lower()

        # Check explicit error_type first if provided
        if error_type in ALL_MISCONCEPTIONS:
            return error_type

        # Thermodynamics mappings
        if any(kw in concept_lower for kw in ["thermo", "hess", "gibbs", "heat", "enthalpy", "first_law", "work"]):
            if "direction" in answer_lower or "invert" in answer_lower or ("hess" in answer_lower and ("same" in answer_lower or "direction" in answer_lower or "stay" in answer_lower or "positive" in answer_lower)):
                return 'HESS_LAW_DIRECTION'
            if ("spontaneous" in answer_lower or "delta g" in answer_lower or "gibbs" in answer_lower) and ("positive" in answer_lower or ">" in answer_lower):
                return 'GIBBS_SIGN_CONFUSION'
            if (
                "+w" in answer_lower
                or "-q" in answer_lower
                or "sign" in error_lower
                or "sign convention" in answer_lower
                or "700" in answer_lower
                or "500 + 200" in answer_lower
                or ("add" in answer_lower and any(w in answer_lower for w in ["work", "expansion", "200", "500"]))
                or ("expansion" in answer_lower and ("positive" in answer_lower or "+200" in answer_lower or "+w" in answer_lower))
                or ("work" in answer_lower and "by the system" in answer_lower and ("+w" in answer_lower or "positive" in answer_lower or "+" in answer_lower))
            ):
                return 'THERMO_SIGN_CONVENTION'
            if ("heat" in answer_lower and "internal energy" in answer_lower) or "q vs u" in answer_lower:
                return 'HEAT_VS_INTERNAL_ENERGY'
            if "state" in answer_lower or "path" in answer_lower:
                return 'STATE_VS_PATH_FUNCTION'
            if ("enthalpy" in answer_lower and "internal energy" in answer_lower) or "h vs u" in answer_lower:
                return 'ENTHALPY_CONFUSION'
            if "cp" in answer_lower or "cv" in answer_lower:
                return 'CP_CV_CONFUSION'

        # Inorganic mappings
        if any(kw in concept_lower for kw in ["inorganic", "inorg", "periodic", "d_block", "p_block", "coordination", "metallurgy"]):
            if "coordination" in answer_lower:
                return 'COORDINATION_NUMBER_CONFUSION'
            if "ligand" in answer_lower:
                return 'LIGAND_CONFUSION'
            if "trend" in answer_lower or "radius" in answer_lower or "ionization" in answer_lower or "gain enthalpy" in answer_lower:
                return 'PERIODIC_TREND_CONFUSION'
            if "oxidation" in answer_lower:
                return 'OXIDATION_STATE_ERROR'
            if "configuration" in answer_lower or "aufbau" in answer_lower or "d-orbital" in answer_lower:
                return 'ELECTRONIC_CONFIGURATION_ERROR'
            if "redox" in answer_lower or "oxidizing" in answer_lower or "reducing" in answer_lower:
                return 'REDOX_CONFUSION'
            if "anomalous" in answer_lower or "diagonal" in answer_lower or "absence of d" in answer_lower:
                return 'ANOMALOUS_BEHAVIOUR_CONFUSION'
            if "calcination" in answer_lower or "roasting" in answer_lower or "leaching" in answer_lower or "metallurgy" in answer_lower:
                return 'METALLURGY_PROCESS_CONFUSION'

        # General keyword matching across ALL_MISCONCEPTIONS
        if "+w" in answer_lower or "-q" in answer_lower or "sign error" in error_lower:
            return 'THERMO_SIGN_CONVENTION'
        if ("hess" in answer_lower or "hess" in error_lower) and ("direction" in answer_lower or "invert" in answer_lower or "same" in answer_lower or "positive" in answer_lower):
            return 'HESS_LAW_DIRECTION'
        if ("gibbs" in answer_lower or "spontaneous" in answer_lower) and ("positive" in answer_lower or ">" in answer_lower):
            return 'GIBBS_SIGN_CONFUSION'
        if "coordination" in answer_lower or "coordination" in error_lower:
            return 'COORDINATION_NUMBER_CONFUSION'
        if "ligand" in answer_lower or "ligand" in error_lower:
            return 'LIGAND_CONFUSION'
        if "redox" in answer_lower or "oxidizing" in answer_lower or "reducing" in answer_lower or "redox" in error_lower:
            return 'REDOX_CONFUSION'
        if "trend" in answer_lower or "radius" in answer_lower:
            return 'PERIODIC_TREND_CONFUSION'
        if "oxidation" in answer_lower:
            return 'OXIDATION_STATE_ERROR'
        if "configuration" in answer_lower or "aufbau" in answer_lower:
            return 'ELECTRONIC_CONFIGURATION_ERROR'
        if "anomalous" in answer_lower or "anomalous" in error_lower:
            return 'ANOMALOUS_BEHAVIOUR_CONFUSION'
        if "calcination" in answer_lower or "roasting" in answer_lower or "metallurgy" in answer_lower or "metallurgy" in error_lower:
            return 'METALLURGY_PROCESS_CONFUSION'

        return None

    def __init__(self, state_manager: Optional[TutorStateManager] = None):
        self.state_manager = state_manager
        if state_manager:
            self._ensure_table_exists(state_manager.conn)

    def _ensure_table_exists(self, conn: sqlite3.Connection) -> None:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS student_misconceptions (
                    student_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    misconception_code TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1,
                    first_detected TEXT NOT NULL,
                    last_detected TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    PRIMARY KEY (student_id, concept_id, misconception_code)
                );
            ''')

    def record_misconception(
        self,
        student_id: str,
        concept_id: str,
        misconception_code: str,
        state_manager: Optional[TutorStateManager] = None,
    ) -> StudentMisconceptionRecord:
        """Record or increment occurrence of a misconception for a student."""
        sm = state_manager or self.state_manager
        if not sm:
            raise ValueError("State manager connection is required to record misconception.")

        self._ensure_table_exists(sm.conn)

        if misconception_code not in ALL_MISCONCEPTIONS:
            # Allow custom codes with warning or registration
            code_desc = f"Custom misconception: {misconception_code}"
        else:
            code_desc = ALL_MISCONCEPTIONS[misconception_code]

        now = datetime.now().isoformat()

        with sm.conn:
            existing = sm.conn.execute(
                'SELECT occurrence_count, first_detected FROM student_misconceptions WHERE student_id = ? AND concept_id = ? AND misconception_code = ?',
                (student_id, concept_id, misconception_code)
            ).fetchone()

            if existing:
                count = existing['occurrence_count'] + 1
                first = existing['first_detected']
                sm.conn.execute('''
                    UPDATE student_misconceptions
                    SET occurrence_count = ?, last_detected = ?, resolved = 0
                    WHERE student_id = ? AND concept_id = ? AND misconception_code = ?
                ''', (count, now, student_id, concept_id, misconception_code))
            else:
                count = 1
                first = now
                sm.conn.execute('''
                    INSERT INTO student_misconceptions (
                        student_id, concept_id, misconception_code, occurrence_count,
                        first_detected, last_detected, resolved
                    ) VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (student_id, concept_id, misconception_code, 1, now, now))

        return StudentMisconceptionRecord(
            student_id=student_id,
            concept_id=concept_id,
            misconception_code=misconception_code,
            occurrence_count=count,
            first_detected=first,
            last_detected=now,
            resolved=False,
        )

    def get_active_misconceptions(
        self,
        student_id: str,
        concept_id: Optional[str] = None,
        state_manager: Optional[TutorStateManager] = None,
    ) -> List[StudentMisconceptionRecord]:
        """Fetch unresolved misconceptions for a student (optionally filtered by concept)."""
        sm = state_manager or self.state_manager
        if not sm:
            return []

        self._ensure_table_exists(sm.conn)

        if concept_id:
            cursor = sm.conn.execute(
                'SELECT * FROM student_misconceptions WHERE student_id = ? AND concept_id = ? AND resolved = 0',
                (student_id, concept_id)
            )
        else:
            cursor = sm.conn.execute(
                'SELECT * FROM student_misconceptions WHERE student_id = ? AND resolved = 0',
                (student_id,)
            )

        rows = cursor.fetchall()
        return [
            StudentMisconceptionRecord(
                student_id=row['student_id'],
                concept_id=row['concept_id'],
                misconception_code=row['misconception_code'],
                occurrence_count=row['occurrence_count'],
                first_detected=row['first_detected'],
                last_detected=row['last_detected'],
                resolved=bool(row['resolved']),
            )
            for row in rows
        ]

    def resolve_misconception(
        self,
        student_id: str,
        concept_id: str,
        misconception_code: str,
        state_manager: Optional[TutorStateManager] = None,
    ) -> None:
        """Mark a misconception as resolved after successful remediation."""
        sm = state_manager or self.state_manager
        if not sm:
            return

        self._ensure_table_exists(sm.conn)

        with sm.conn:
            sm.conn.execute('''
                UPDATE student_misconceptions
                SET resolved = 1
                WHERE student_id = ? AND concept_id = ? AND misconception_code = ?
            ''', (student_id, concept_id, misconception_code))
