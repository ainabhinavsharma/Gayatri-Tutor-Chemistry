from __future__ import annotations
import sqlite3
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from core.db import get_safe_db_connection, run_migrations
from core.config import DB_PATH
from pathlib import Path
import json
from datetime import datetime

@dataclass
class ConceptMastery:
    user_id: str
    concept_id: str
    attempts: int
    correct_count: int
    difficulty_exposure: float
    last_reviewed: str
    confidence_estimate: float

@dataclass
class AssessmentRecord:
    assessment_id: str
    user_id: str
    topic: str
    chapter: str
    assessment_type: str
    difficulty: str
    questions_json: str
    answers_json: str
    score: float
    started_at: str
    completed_at: str

class TutorStateManager:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
        self._db_conn = None
        self._create_schema()
        
    @property
    def conn(self) -> sqlite3.Connection:
        if self._db_conn is None:
            self._db_conn = get_safe_db_connection(self.db_path)
        return self._db_conn

    def _create_schema(self) -> None:
        conn = self.conn
        
        def initial_schema(c):
            c.executescript('''
                CREATE TABLE IF NOT EXISTS concept_mastery (
                    user_id TEXT,
                    concept_id TEXT,
                    attempts INTEGER DEFAULT 0,
                    correct_count INTEGER DEFAULT 0,
                    difficulty_exposure REAL DEFAULT 0.0,
                    last_reviewed TEXT,
                    confidence_estimate REAL DEFAULT 0.0,
                    PRIMARY KEY (user_id, concept_id)
                );
                
                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    topic TEXT,
                    chapter TEXT,
                    assessment_type TEXT,
                    difficulty TEXT,
                    questions_json TEXT,
                    answers_json TEXT,
                    score REAL,
                    started_at TEXT,
                    completed_at TEXT
                );
            ''')
            
        migrations = {
            200: ("initial_tutor_state_schema", initial_schema),
        }
        
        run_migrations(conn, migrations)

    def get_concept_mastery(self, concept_id: str, user_id: str = "local_user_1") -> ConceptMastery:
        conn = self.conn
        cursor = conn.execute("SELECT * FROM concept_mastery WHERE user_id = ? AND concept_id = ?", (user_id, concept_id))
        row = cursor.fetchone()
        if not row:
            return ConceptMastery(
                user_id=user_id,
                concept_id=concept_id,
                attempts=0,
                correct_count=0,
                difficulty_exposure=0.0,
                last_reviewed=datetime.now().isoformat(),
                confidence_estimate=0.0
            )
        return ConceptMastery(
            user_id=row["user_id"],
            concept_id=row["concept_id"],
            attempts=row["attempts"],
            correct_count=row["correct_count"],
            difficulty_exposure=row["difficulty_exposure"],
            last_reviewed=row["last_reviewed"],
            confidence_estimate=row["confidence_estimate"]
        )

    def update_concept_mastery(self, mastery: ConceptMastery) -> None:
        with self.conn:
            self.conn.execute('''
                INSERT INTO concept_mastery (user_id, concept_id, attempts, correct_count, difficulty_exposure, last_reviewed, confidence_estimate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, concept_id) DO UPDATE SET
                    attempts=excluded.attempts,
                    correct_count=excluded.correct_count,
                    difficulty_exposure=excluded.difficulty_exposure,
                    last_reviewed=excluded.last_reviewed,
                    confidence_estimate=excluded.confidence_estimate
            ''', (
                mastery.user_id, mastery.concept_id, mastery.attempts, 
                mastery.correct_count, mastery.difficulty_exposure, 
                mastery.last_reviewed, mastery.confidence_estimate
            ))

    def save_assessment(self, record: AssessmentRecord) -> None:
        with self.conn:
            self.conn.execute('''
                INSERT INTO assessments (assessment_id, user_id, topic, chapter, assessment_type, difficulty, questions_json, answers_json, score, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.assessment_id, record.user_id, record.topic, record.chapter, 
                record.assessment_type, record.difficulty, record.questions_json, 
                record.answers_json, record.score, record.started_at, record.completed_at
            ))

_tutor_state_manager = None
def get_tutor_state_manager() -> TutorStateManager:
    global _tutor_state_manager
    if _tutor_state_manager is None:
        _tutor_state_manager = TutorStateManager()
    return _tutor_state_manager
