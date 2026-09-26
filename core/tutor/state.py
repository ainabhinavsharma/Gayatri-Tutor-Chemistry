"""Gayatri AI - Student Learning State and Evidence persistence (Phase 1).

Implements student-scoped concept mastery, append-only learning event evidence,
turn ID generation, schema migrations, and idempotent event updates.
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.config import DB_PATH
from core.db import get_safe_db_connection, run_migrations


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
class StudentConceptMastery:
    student_id: str
    concept_id: str
    mastery: float = 0.0
    confidence: float = 0.0
    exposure_count: int = 0
    correct_count: int = 0
    error_count: int = 0
    hint_count: int = 0
    last_practiced: str = ''
    next_review_at: str = ''
    difficulty_level: float = 0.5
    learning_status: str = 'NEW'

    def to_dict(self) -> dict:
        return {
            'student_id': self.student_id,
            'concept_id': self.concept_id,
            'mastery': self.mastery,
            'confidence': self.confidence,
            'exposure_count': self.exposure_count,
            'correct_count': self.correct_count,
            'error_count': self.error_count,
            'hint_count': self.hint_count,
            'last_practiced': self.last_practiced,
            'next_review_at': self.next_review_at,
            'difficulty_level': self.difficulty_level,
            'learning_status': self.learning_status,
        }


@dataclass
class LearningEvent:
    event_id: str
    student_id: str
    session_id: str
    turn_id: str
    concept_id: str
    question_id: str = ''
    timestamp: str = ''
    difficulty: float = 0.5
    question_type: str = 'conceptual'
    correctness: str = 'correct'  # 'correct', 'partially_correct', 'incorrect', 'uncertain'
    confidence: float = 0.0
    hint_used: int = 0
    response_time: float = 0.0
    misconception_code: str = ''
    source: str = 'chat'

    @property
    def misconception(self) -> str:
        """Alias for misconception_code."""
        return self.misconception_code

    @misconception.setter
    def misconception(self, value: str) -> None:
        self.misconception_code = value

    def to_dict(self) -> dict:
        return {
            'event_id': self.event_id,
            'student_id': self.student_id,
            'session_id': self.session_id,
            'turn_id': self.turn_id,
            'concept_id': self.concept_id,
            'question_id': self.question_id,
            'timestamp': self.timestamp,
            'difficulty': self.difficulty,
            'question_type': self.question_type,
            'correctness': self.correctness,
            'confidence': self.confidence,
            'hint_used': self.hint_used,
            'response_time': self.response_time,
            'misconception': self.misconception_code,
            'misconception_code': self.misconception_code,
            'source': self.source,
        }


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


def generate_turn_id(student_id: str = 'default_student', session_id: str = 'default_session') -> tuple[str, str]:
    '''Generate a unique turn ID and timestamp ISO string (P1-T04).'''
    timestamp = datetime.now().isoformat()
    rand_part = uuid.uuid4().hex[:8]
    turn_id = f'turn_{datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]}_{rand_part}'
    return turn_id, timestamp


class TutorStateManager:
    '''Manages persistent student learning state, evidence logs, and assessment records.'''

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
        self._local = threading.local()
        self._is_memory = str(self.db_path) == ":memory:"
        self._shared_conn = None
        self._create_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._is_memory:
            if self._shared_conn is None:
                self._shared_conn = get_safe_db_connection(self.db_path)
            return self._shared_conn
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = get_safe_db_connection(self.db_path)
            self._local.conn = conn
        return conn

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

        def student_learning_state_v1(c):
            c.executescript('''
                CREATE TABLE IF NOT EXISTS student_concept_mastery (
                    student_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    mastery REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    exposure_count INTEGER DEFAULT 0,
                    correct_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_practiced TEXT DEFAULT '',
                    next_review_at TEXT DEFAULT '',
                    difficulty_level REAL DEFAULT 0.5,
                    PRIMARY KEY (student_id, concept_id)
                );

                CREATE TABLE IF NOT EXISTS learning_events (
                    event_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    question_id TEXT DEFAULT '',
                    timestamp TEXT NOT NULL,
                    difficulty REAL DEFAULT 0.5,
                    question_type TEXT DEFAULT 'conceptual',
                    correctness TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    hint_used INTEGER DEFAULT 0,
                    response_time REAL DEFAULT 0.0,
                    misconception_code TEXT DEFAULT '',
                    source TEXT DEFAULT 'chat'
                );
            ''')

        def assessment_engine_v1(c):
            c.executescript('''
                CREATE TABLE IF NOT EXISTS assessment_sessions (
                    assessment_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    concepts_json TEXT NOT NULL,
                    question_ids_json TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT DEFAULT '',
                    status TEXT DEFAULT 'IN_PROGRESS',
                    score REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS assessment_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    student_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    score_fraction REAL NOT NULL,
                    feedback TEXT DEFAULT '',
                    submitted_at TEXT NOT NULL
                );
            ''')

        def turn_lifecycle_v1(c):
            c.executescript('''
                CREATE TABLE IF NOT EXISTS turn_lifecycle (
                    turn_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    concept_id TEXT DEFAULT '',
                    stage TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error_detail TEXT DEFAULT ''
                );
            ''')

        def student_learning_state_v2(c):
            try:
                c.execute('ALTER TABLE student_concept_mastery ADD COLUMN hint_count INTEGER DEFAULT 0;')
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
            try:
                c.execute("ALTER TABLE student_concept_mastery ADD COLUMN learning_status TEXT DEFAULT 'NEW';")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise

        def assessment_engine_v2(c):
            c.executescript('''
                CREATE TABLE IF NOT EXISTS assessment (
                    assessment_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    concepts_json TEXT NOT NULL,
                    question_ids_json TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT DEFAULT '',
                    status TEXT DEFAULT 'IN_PROGRESS',
                    score REAL DEFAULT 0.0
                );

                CREATE TABLE IF NOT EXISTS assessment_question (
                    id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    difficulty INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    rubric TEXT DEFAULT '',
                    hint TEXT DEFAULT '',
                    explanation TEXT DEFAULT '',
                    common_misconceptions TEXT DEFAULT '[]',
                    source TEXT DEFAULT 'NCERT'
                );

                CREATE TABLE IF NOT EXISTS assessment_attempt (
                    attempt_id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    student_answer TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    score_fraction REAL NOT NULL,
                    feedback TEXT DEFAULT '',
                    submitted_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS score (
                    score_id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    total_score REAL NOT NULL,
                    max_possible REAL NOT NULL,
                    score_percentage REAL NOT NULL,
                    strengths_json TEXT DEFAULT '[]',
                    weaknesses_json TEXT DEFAULT '[]',
                    completed_at TEXT NOT NULL
                );
            ''')

        def database_hardening_v1(c):
            c.executescript('''
                -- Indexes on learning_events for fast lookups
                CREATE INDEX IF NOT EXISTS idx_learning_events_student_concept ON learning_events(student_id, concept_id);
                CREATE INDEX IF NOT EXISTS idx_learning_events_turn_id ON learning_events(turn_id);
                CREATE INDEX IF NOT EXISTS idx_learning_events_timestamp ON learning_events(timestamp);

                -- Index on turn_lifecycle for student and stage queries
                CREATE INDEX IF NOT EXISTS idx_turn_lifecycle_student_stage ON turn_lifecycle(student_id, stage);

                -- Index on student_concept_mastery for spaced review lookups
                CREATE INDEX IF NOT EXISTS idx_student_concept_mastery_review ON student_concept_mastery(student_id, next_review_at);

                -- Indexes on assessment tables
                CREATE INDEX IF NOT EXISTS idx_assessment_question_assessment ON assessment_question(assessment_id);
                CREATE INDEX IF NOT EXISTS idx_assessment_attempt_assessment ON assessment_attempt(assessment_id);
                CREATE INDEX IF NOT EXISTS idx_score_assessment ON score(assessment_id);
                CREATE INDEX IF NOT EXISTS idx_score_student ON score(student_id);
            ''')

        migrations = {
            200: ('initial_tutor_state_schema', initial_schema),
            201: ('student_learning_state_v1', student_learning_state_v1),
            202: ('assessment_engine_v1', assessment_engine_v1),
            203: ('turn_lifecycle_v1', turn_lifecycle_v1),
            204: ('student_learning_state_v2', student_learning_state_v2),
            205: ('assessment_engine_v2', assessment_engine_v2),
            206: ('database_hardening_v1', database_hardening_v1),
        }

        run_migrations(conn, migrations)

    # -- Legacy ConceptMastery support --

    def get_concept_mastery(self, concept_id: str, user_id: str = 'local_user_1') -> ConceptMastery:
        conn = self.conn
        cursor = conn.execute('SELECT * FROM concept_mastery WHERE user_id = ? AND concept_id = ?', (user_id, concept_id))
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
            user_id=row['user_id'],
            concept_id=row['concept_id'],
            attempts=row['attempts'],
            correct_count=row['correct_count'],
            difficulty_exposure=row['difficulty_exposure'],
            last_reviewed=row['last_reviewed'],
            confidence_estimate=row['confidence_estimate']
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

    # -- Student-Scoped Learning State (Phase 1 P1-T01 to P1-T05) --

    def get_student_concept_mastery(self, student_id: str, concept_id: str) -> StudentConceptMastery:
        '''Get student-scoped concept mastery (P1-T01).'''
        from core.security.validation import validate_concept_id, validate_student_id
        student_id = validate_student_id(student_id)
        concept_id = validate_concept_id(concept_id)

        cursor = self.conn.execute(
            'SELECT * FROM student_concept_mastery WHERE student_id = ? AND concept_id = ?',
            (student_id, concept_id)
        )
        row = cursor.fetchone()
        if not row:
            return StudentConceptMastery(student_id=student_id, concept_id=concept_id)

        keys = row.keys()
        return StudentConceptMastery(
            student_id=row['student_id'],
            concept_id=row['concept_id'],
            mastery=row['mastery'],
            confidence=row['confidence'],
            exposure_count=row['exposure_count'],
            correct_count=row['correct_count'],
            error_count=row['error_count'],
            hint_count=row['hint_count'] if 'hint_count' in keys else 0,
            last_practiced=row['last_practiced'],
            next_review_at=row['next_review_at'],
            difficulty_level=row['difficulty_level'],
            learning_status=row['learning_status'] if 'learning_status' in keys else 'NEW',
        )

    def record_learning_event(self, event: LearningEvent) -> bool:
        '''Record an append-only evidence event idempotently and update student mastery (P1-T03 and P1-T05).

        Returns True if event was newly recorded, False if event_id already exists (idempotent).
        '''
        from core.security.validation import validate_concept_id, validate_student_id
        if not event.student_id or not str(event.student_id).strip():
            raise ValueError("event.student_id must not be empty")
        validate_student_id(event.student_id)
        validate_concept_id(event.concept_id)

        valid_correctness = {'correct', 'incorrect', 'partially_correct', 'uncertain'}
        if event.correctness not in valid_correctness:
            raise ValueError(f"event.correctness '{event.correctness}' must be one of {valid_correctness}")
        if event.difficulty < 0.0 or event.difficulty > 5.0:
            raise ValueError(f"event.difficulty {event.difficulty} must be between 0.0 and 5.0")

        with self.conn:
            # Check idempotency (P1-T05)
            existing = self.conn.execute('SELECT 1 FROM learning_events WHERE event_id = ?', (event.event_id,)).fetchone()
            if existing:
                return False

            # Append evidence event
            self.conn.execute('''
                INSERT INTO learning_events (
                    event_id, student_id, session_id, turn_id, concept_id, question_id,
                    timestamp, difficulty, question_type, correctness, confidence,
                    hint_used, response_time, misconception_code, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.student_id, event.session_id, event.turn_id,
                event.concept_id, event.question_id, event.timestamp or datetime.now().isoformat(),
                event.difficulty, event.question_type, event.correctness, event.confidence,
                event.hint_used, event.response_time, event.misconception_code, event.source
            ))

            # Audit #43: 'uncertain' evaluation must NOT mutate student mastery state
            if event.correctness == 'uncertain':
                return True

            # Calculate evidence-driven student mastery update
            current = self.get_student_concept_mastery(event.student_id, event.concept_id)

            new_exposure = current.exposure_count + 1
            new_correct = current.correct_count + (1 if event.correctness == 'correct' else 0)
            new_error = current.error_count + (1 if event.correctness == 'incorrect' else 0)
            new_hints = current.hint_count + (1 if event.hint_used > 0 else 0)

            # Master delta rules
            if event.correctness == 'correct':
                delta = 0.1
            elif event.correctness == 'partially_correct':
                delta = 0.05
            else:  # incorrect
                delta = -0.1

            new_mastery = max(0.0, min(1.0, current.mastery + delta))
            new_confidence = min(1.0, current.confidence + 0.1)

            from core.learning.progress import get_status_label
            from core.learning.scheduler import SpacedReviewScheduler
            is_due = SpacedReviewScheduler().is_review_due(current.next_review_at)
            new_status = get_status_label(new_mastery, new_exposure, is_due)

            self.conn.execute('''
                INSERT INTO student_concept_mastery (
                    student_id, concept_id, mastery, confidence, exposure_count,
                    correct_count, error_count, hint_count, last_practiced, next_review_at, difficulty_level, learning_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, concept_id) DO UPDATE SET
                    mastery = excluded.mastery,
                    confidence = excluded.confidence,
                    exposure_count = excluded.exposure_count,
                    correct_count = excluded.correct_count,
                    error_count = excluded.error_count,
                    hint_count = excluded.hint_count,
                    last_practiced = excluded.last_practiced,
                    difficulty_level = excluded.difficulty_level,
                    learning_status = excluded.learning_status
            ''', (
                event.student_id, event.concept_id, new_mastery, new_confidence,
                new_exposure, new_correct, new_error, new_hints, event.timestamp or datetime.now().isoformat(),
                current.next_review_at, event.difficulty, new_status
            ))

            return True

    def get_learning_events(self, student_id: str, concept_id: str | None = None) -> list[LearningEvent]:
        """Fetch historical learning events for a student, optionally filtered by concept."""
        from core.security.validation import validate_concept_id, validate_student_id
        student_id = validate_student_id(student_id)
        if concept_id:
            concept_id = validate_concept_id(concept_id)

        if concept_id:
            cursor = self.conn.execute(
                'SELECT * FROM learning_events WHERE student_id = ? AND concept_id = ? ORDER BY timestamp ASC',
                (student_id, concept_id)
            )
        else:
            cursor = self.conn.execute(
                'SELECT * FROM learning_events WHERE student_id = ? ORDER BY timestamp ASC',
                (student_id,)
            )

        events: list[LearningEvent] = []
        for row in cursor.fetchall():
            keys = row.keys()
            events.append(LearningEvent(
                event_id=row['event_id'],
                student_id=row['student_id'],
                session_id=row['session_id'],
                turn_id=row['turn_id'],
                concept_id=row['concept_id'],
                question_id=row['question_id'],
                timestamp=row['timestamp'],
                difficulty=row['difficulty'],
                question_type=row['question_type'],
                correctness=row['correctness'],
                confidence=row['confidence'],
                hint_used=row['hint_used'],
                response_time=row['response_time'] if 'response_time' in keys else 0.0,
                misconception_code=row['misconception_code'] if 'misconception_code' in keys else '',
                source=row['source'] if 'source' in keys else 'chat',
            ))
        return events

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


def get_tutor_state_manager(db_path: str | Path | None = None) -> TutorStateManager:
    global _tutor_state_manager
    if _tutor_state_manager is None or db_path is not None:
        _tutor_state_manager = TutorStateManager(db_path=db_path)
    return _tutor_state_manager

