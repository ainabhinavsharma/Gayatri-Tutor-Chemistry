"""Gayatri AI — Adaptive Learning Engine, Mastery Model & Event Tracking (Phases 3, 4, 5).

Implements:
1. Transparent Mastery Model (Section 21): 0.0 <= mastery <= 1.0
2. Adaptive Learning Policy (Section 24): mastery threshold routing & prerequisite remediation
3. Student State Representation (Section 20): demo_student_001 profile
4. Event Logging System (Section 28): JSONL persistent event telemetry
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gayatri.tutor.adaptive")

# Default paths
from core.config import DATA_DIR
DEFAULT_STUDENT_FILE = DATA_DIR / "student_profile.json"
DEFAULT_EVENT_LOG = DATA_DIR / "events.jsonl"


# ── Section 21: Mastery Model Constants ─────────────────────────────────

DELTA_CORRECT_FIRST_ATTEMPT: float = 0.10
DELTA_CORRECT_AFTER_HINT: float = 0.05
DELTA_PARTIAL: float = 0.02
DELTA_INCORRECT: float = -0.05
DELTA_REPEATED_MISCONCEPTION: float = -0.03

MASTERY_MIN: float = 0.0
MASTERY_MAX: float = 1.0


# ── Section 20: Student State Data Structure ─────────────────────────────

@dataclass
class StudentProfile:
    """Persistent student profile matching Section 20 of Master Plan."""
    student_id: str = "student_001"
    name: str = "Student"
    level: str = "class_11"
    target: str = "chemistry_foundation"
    current_topic: str = "Thermodynamics"
    current_concept: str = "THERMO_FIRST_LAW"
    mastery: Dict[str, float] = field(default_factory=dict)
    misconceptions: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    active_hint_level: int = 0
    current_mode: str = "EXPLAIN"

    def get_mastery(self, concept_id: str, default: float = 0.0) -> float:
        """Get current mastery score for a concept, defaulting to initial foundation."""
        return self.mastery.get(concept_id, default)

    def set_mastery(self, concept_id: str, score: float) -> float:
        """Set mastery score bounded strictly within [0.0, 1.0]."""
        clamped = max(MASTERY_MIN, min(MASTERY_MAX, round(score, 3)))
        self.mastery[concept_id] = clamped
        return clamped

    def update_mastery(self, concept_id: str, delta: float) -> tuple[float, float]:
        """Apply delta to concept mastery, returning (previous_mastery, new_mastery)."""
        prev = self.get_mastery(concept_id)
        new_val = self.set_mastery(concept_id, prev + delta)
        return prev, new_val

    def save_to_file(self, file_path: Path | None = None) -> None:
        """Persist student state to JSON file."""
        target = file_path or DEFAULT_STUDENT_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: Path | None = None) -> StudentProfile:
        """Load student state from JSON file or return default demo student."""
        target = file_path or DEFAULT_STUDENT_FILE
        if target.exists():
            try:
                with open(target, encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**data)
            except Exception as exc:
                logger.warning(f"Failed to load student from {target}: {exc}; creating default")
        # Clean-slate student profile for self-testing
        inst = cls()
        inst.save_to_file(target)
        return inst


# ── Section 28: Event Logging Engine ─────────────────────────────────────

class EventLogger:
    """Logs educational telemetry events per Section 28 of Master Plan."""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path or DEFAULT_EVENT_LOG
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        event_type: str,
        student_id: str,
        concept_id: str,
        details: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Record an event to the local JSONL event log."""
        record = {
            "event": event_type,
            "student_id": student_id,
            "concept_id": concept_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(details or {}),
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.error(f"Failed to append event log: {exc}")
        return record

    def get_recent_events(self, student_id: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent events from the event log with optional filtering."""
        if not self.log_path.exists():
            return []
        events = []
        try:
            with open(self.log_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if student_id is None or record.get("student_id") == student_id:
                            events.append(record)
        except Exception as exc:
            logger.error(f"Failed to read events: {exc}")
        return events[-limit:]


# ── Section 24: Adaptive Learning Algorithm ──────────────────────────────

class AdaptiveLearningEngine:
    """Implements the deterministic adaptive learning policy of Section 24."""

    @staticmethod
    def evaluate_mastery_delta(
        result: str,
        hint_level: int = 0,
        is_repeated_misconception: bool = False,
    ) -> float:
        """Calculate mastery delta based on Section 21 rules."""
        res_upper = result.upper()
        if res_upper == "CORRECT":
            if hint_level > 0:
                return DELTA_CORRECT_AFTER_HINT
            return DELTA_CORRECT_FIRST_ATTEMPT
        elif res_upper == "PARTIALLY_CORRECT":
            return DELTA_PARTIAL
        elif res_upper == "INCORRECT":
            if is_repeated_misconception:
                return DELTA_INCORRECT + DELTA_REPEATED_MISCONCEPTION
            return DELTA_INCORRECT
        return 0.0

    @staticmethod
    def decide_next_action(
        concept_id: str,
        student: StudentProfile,
        prerequisites: List[str],
        prereq_masteries: Dict[str, float],
    ) -> Dict[str, Any]:
        """Apply Section 24 Adaptive Learning Decision Rules.

        Rules:
        IF mastery >= 0.80 -> consider concept mastered
        ELSE IF prerequisite mastery < 0.50 -> REMEDIATE prerequisite
        ELSE IF mastery < 0.40 -> EXPLAIN / REMEDIATE
        ELSE IF mastery < 0.70 -> QUESTION + HINT
        ELSE -> harder QUESTION
        """
        mastery = student.get_mastery(concept_id)

        # Check weakest prerequisite
        weakest_prereq = None
        weakest_score = 1.0
        for p in prerequisites:
            p_score = prereq_masteries.get(p, student.get_mastery(p))
            if p_score < weakest_score:
                weakest_score = p_score
                weakest_prereq = p

        # 1. Concept Mastered
        if mastery >= 0.80:
            return {
                "action": "MASTERED",
                "recommended_mode": "SUMMARY",
                "target_concept": concept_id,
                "reason": f"Concept mastery ({mastery:.0%}) meets master threshold (>= 80%)",
                "difficulty": 0.8,
            }

        # 2. Prerequisite Deficit
        if weakest_prereq and weakest_score < 0.50:
            return {
                "action": "REMEDIATE_PREREQUISITE",
                "recommended_mode": "REMEDIATE",
                "target_concept": weakest_prereq,
                "original_concept": concept_id,
                "prerequisite_score": weakest_score,
                "reason": f"Prerequisite '{weakest_prereq}' mastery ({weakest_score:.0%}) below foundation threshold (< 50%)",
                "difficulty": 0.3,
            }

        # 3. Low Concept Mastery
        if mastery < 0.40:
            return {
                "action": "EXPLAIN_CONCEPT",
                "recommended_mode": "EXPLAIN",
                "target_concept": concept_id,
                "reason": f"Concept mastery ({mastery:.0%}) below working threshold (< 40%)",
                "difficulty": 0.3,
            }

        # 4. Developing Concept Mastery
        if mastery < 0.70:
            return {
                "action": "TEST_AND_HINT",
                "recommended_mode": "QUESTION",
                "target_concept": concept_id,
                "reason": f"Concept mastery ({mastery:.0%}) in active practice range (40%-70%)",
                "difficulty": 0.5,
            }

        # 5. Advanced Practice
        return {
            "action": "CHALLENGE_QUESTION",
            "recommended_mode": "QUESTION",
            "target_concept": concept_id,
            "reason": f"Concept mastery ({mastery:.0%}) near mastery (>= 70%)",
            "difficulty": 0.7,
        }
