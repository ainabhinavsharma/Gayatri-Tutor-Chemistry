"""Gayatri AI — Teacher & Parent Governance & Controls.

Provides administrative controls, daily learning time budgeting,
PIN-protected configuration locks, and exportable student mastery reports.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import secrets
import sqlite3
import threading
from datetime import datetime, date
from pathlib import Path

from core.db import get_safe_db_connection
from core.knowledge_graph import LearningDependencyGraph

logger = logging.getLogger("gayatri.governance")

DEFAULT_ADMIN_PIN = "1234"


def _hash_pin(pin: str) -> str:
    """Hash a PIN using SHA-256 for secure non-plaintext storage."""
    return hashlib.sha256(pin.strip().encode("utf-8")).hexdigest()


class GovernanceManager:
    """Manages parental controls, daily time budgets, and student report generation."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            from core.config import DB_PATH
            self.db_path = Path(DB_PATH)
        else:
            self.db_path = Path(db_path)

        self._lock = threading.RLock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return get_safe_db_connection(self.db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS governance_settings (
                        key TEXT PRIMARY KEY,
                        val TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS student_daily_usage (
                        profile_id TEXT NOT NULL,
                        usage_date TEXT NOT NULL,
                        minutes_spent REAL NOT NULL DEFAULT 0.0,
                        PRIMARY KEY (profile_id, usage_date)
                    );
                    """
                )
                # Seed default admin PIN if not set
                cur = conn.execute("SELECT val FROM governance_settings WHERE key = 'admin_pin';")
                if not cur.fetchone():
                    default_pin = os.environ.get("GAYATRI_ADMIN_PIN", DEFAULT_ADMIN_PIN)
                    conn.execute(
                        "INSERT INTO governance_settings (key, val) VALUES ('admin_pin', ?);",
                        (_hash_pin(default_pin),),
                    )
            conn.close()

    def verify_pin(self, entered_pin: str) -> bool:
        """Verify the parental/teacher administration PIN using timing-safe comparison."""
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute("SELECT val FROM governance_settings WHERE key = 'admin_pin';").fetchone()
                if not row:
                    return False
                stored = row["val"]
                entered_hash = _hash_pin(entered_pin)
                # Check hashed match
                if secrets.compare_digest(stored, entered_hash):
                    return True
                # Legacy plaintext check with automatic migration to hash
                if secrets.compare_digest(stored, entered_pin.strip()):
                    with conn:
                        conn.execute(
                            "UPDATE governance_settings SET val = ? WHERE key = 'admin_pin';",
                            (entered_hash,),
                        )
                    return True
                return False
            finally:
                conn.close()

    def set_pin(self, old_pin: str, new_pin: str) -> bool:
        """Update the administration PIN if the current PIN matches."""
        if not self.verify_pin(old_pin):
            return False
        with self._lock:
            conn = self._get_conn()
            try:
                with conn:
                    conn.execute(
                        "UPDATE governance_settings SET val = ? WHERE key = 'admin_pin';",
                        (_hash_pin(new_pin),),
                    )
                return True
            finally:
                conn.close()

    def record_usage(self, profile_id: str, minutes: float) -> float:
        """Record learning time in minutes for today and return new total."""
        today = date.today().isoformat()
        with self._lock:
            conn = self._get_conn()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO student_daily_usage (profile_id, usage_date, minutes_spent)
                        VALUES (?, ?, ?)
                        ON CONFLICT(profile_id, usage_date) DO UPDATE SET minutes_spent = minutes_spent + ?;
                        """,
                        (profile_id, today, minutes, minutes),
                    )
                    row = conn.execute(
                        "SELECT minutes_spent FROM student_daily_usage WHERE profile_id = ? AND usage_date = ?;",
                        (profile_id, today),
                    ).fetchone()
                    return row["minutes_spent"] if row else minutes
            finally:
                conn.close()

    def check_time_limit(self, profile_id: str, daily_limit_minutes: float = 120.0) -> bool:
        """Return True if the student has remaining time, False if daily limit is reached."""
        today = date.today().isoformat()
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT minutes_spent FROM student_daily_usage WHERE profile_id = ? AND usage_date = ?;",
                    (profile_id, today),
                ).fetchone()
                current = row["minutes_spent"] if row else 0.0
                return current < daily_limit_minutes
            finally:
                conn.close()

    def export_progress_report(
        self,
        profile_id: str,
        student_name: str,
        ldg: LearningDependencyGraph,
        format: str = "json",
    ) -> str:
        """Export a comprehensive progress and mastery report for parents or teachers."""
        concepts = ldg.list_concepts()
        mastered = [c for c in concepts if ldg.is_mastered(c.id)]
        practicing = [c for c in concepts if not ldg.is_mastered(c.id) and c.exposure_count > 0]
        unintroduced = [c for c in concepts if c.exposure_count == 0]

        data = {
            "profile_id": profile_id,
            "student_name": student_name,
            "report_generated_at": datetime.now().isoformat(),
            "total_concepts": len(concepts),
            "mastered_count": len(mastered),
            "practicing_count": len(practicing),
            "unintroduced_count": len(unintroduced),
            "mastery_percentage": round((len(mastered) / len(concepts) * 100), 1) if concepts else 0.0,
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "subject": c.subject,
                    "mastery": round(c.mastery, 2),
                    "exposure_count": c.exposure_count,
                    "status": "Mastered" if ldg.is_mastered(c.id) else ("In Progress" if c.exposure_count > 0 else "Not Started"),
                }
                for c in concepts
            ],
        }

        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Concept ID", "Name", "Subject", "Mastery", "Exposures", "Status"])
            for item in data["concepts"]:
                writer.writerow([item["id"], item["name"], item["subject"], item["mastery"], item["exposure_count"], item["status"]])
            return output.getvalue()

        return json.dumps(data, indent=2)
