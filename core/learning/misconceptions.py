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
    'THERMO_SIGN_CONVENTION': 'Confusing work/heat sign convention (+w/-w, +q/-q).',
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


class MisconceptionTracker:
    """Manages recording, querying, and resolving student misconception records."""

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
