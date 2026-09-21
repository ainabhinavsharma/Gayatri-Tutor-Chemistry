"""Turn Lifecycle Persistence and Recovery Manager (Phase 10).

Tracks explicit turn lifecycle stages:
TURN_STARTED -> EVALUATION_STARTED -> RESPONSE_GENERATED -> EVALUATION_COMPLETED -> LEARNING_STATE_UPDATED -> TURN_COMMITTED
Or TURN_ABORTED on failure.

Provides automatic startup recovery for incomplete turns (P10-T02).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

from core.db import execute_with_retry

if TYPE_CHECKING:
    from core.tutor.state import TutorStateManager

logger = logging.getLogger("gayatri.tutor.lifecycle")


class TurnStage(str, Enum):
    TURN_STARTED = "TURN_STARTED"
    EVALUATION_STARTED = "EVALUATION_STARTED"
    RESPONSE_GENERATED = "RESPONSE_GENERATED"
    EVALUATION_COMPLETED = "EVALUATION_COMPLETED"
    LEARNING_STATE_UPDATED = "LEARNING_STATE_UPDATED"
    TURN_COMMITTED = "TURN_COMMITTED"
    TURN_ABORTED = "TURN_ABORTED"


@dataclass
class TurnLifecycleRecord:
    turn_id: str
    student_id: str
    session_id: str
    concept_id: str
    stage: TurnStage
    started_at: str
    updated_at: str
    error_detail: str = ""


class TurnLifecycleManager:
    """Manages transactional turn lifecycle state recording and crash recovery."""

    def __init__(self, state_manager: TutorStateManager):
        self.state_manager = state_manager

    def start_turn(
        self,
        turn_id: str,
        student_id: str,
        session_id: str,
        concept_id: str = "",
    ) -> TurnLifecycleRecord:
        """Record the start of a turn (P10-T01)."""
        now = datetime.now().isoformat()

        def _do_start():
            with self.state_manager.conn:
                self.state_manager.conn.execute('''
                    INSERT INTO turn_lifecycle (
                        turn_id, student_id, session_id, concept_id, stage, started_at, updated_at, error_detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '')
                    ON CONFLICT(turn_id) DO UPDATE SET
                        stage = excluded.stage,
                        updated_at = excluded.updated_at
                ''', (turn_id, student_id, session_id, concept_id, TurnStage.TURN_STARTED.value, now, now))

        execute_with_retry(_do_start, max_retries=5, base_delay=0.1, max_delay=1.0)

        return TurnLifecycleRecord(
            turn_id=turn_id,
            student_id=student_id,
            session_id=session_id,
            concept_id=concept_id,
            stage=TurnStage.TURN_STARTED,
            started_at=now,
            updated_at=now,
        )

    def update_stage(self, turn_id: str, stage: TurnStage, error_detail: str = "") -> None:
        """Advance turn stage in database (P10-T01)."""
        now = datetime.now().isoformat()

        def _do_update():
            with self.state_manager.conn:
                self.state_manager.conn.execute('''
                    UPDATE turn_lifecycle
                    SET stage = ?, updated_at = ?, error_detail = ?
                    WHERE turn_id = ?
                ''', (stage.value, now, error_detail, turn_id))

        execute_with_retry(_do_update, max_retries=5, base_delay=0.1, max_delay=1.0)

    def recover_incomplete_turns(self) -> dict:
        """Scan DB on startup, find interrupted turns, and recover or abort safely (P10-T02)."""
        def _do_recover():
            cursor = self.state_manager.conn.execute('''
                SELECT * FROM turn_lifecycle
                WHERE stage NOT IN ('TURN_COMMITTED', 'TURN_ABORTED')
            ''')
            rows = cursor.fetchall()
            if not rows:
                return {"recovered_count": 0, "aborted_count": 0}

            recovered_count = 0
            aborted_count = 0
            now = datetime.now().isoformat()

            with self.state_manager.conn:
                for row in rows:
                    t_id = row["turn_id"]
                    st = row["stage"]

                    # Check if learning event was already recorded for this turn ID (idempotency guard)
                    evt_row = self.state_manager.conn.execute(
                        "SELECT 1 FROM learning_events WHERE turn_id = ?", (t_id,)
                    ).fetchone()

                    if evt_row or st == TurnStage.LEARNING_STATE_UPDATED.value:
                        # Learning event exists -> mark as COMMITTED cleanly
                        self.state_manager.conn.execute(
                            "UPDATE turn_lifecycle SET stage = ?, updated_at = ? WHERE turn_id = ?",
                            (TurnStage.TURN_COMMITTED.value, now, t_id)
                        )
                        recovered_count += 1
                    else:
                        # Unfinished turn before learning state mutation -> mark as ABORTED safely
                        self.state_manager.conn.execute(
                            "UPDATE turn_lifecycle SET stage = ?, updated_at = ?, error_detail = ? WHERE turn_id = ?",
                            (TurnStage.TURN_ABORTED.value, now, "Turn interrupted before commitment during system restart.", t_id)
                        )
                        aborted_count += 1

            logger.info(f"Startup Turn Recovery: {recovered_count} recovered, {aborted_count} aborted cleanly.")
            return {"recovered_count": recovered_count, "aborted_count": aborted_count}

        return execute_with_retry(_do_recover, max_retries=5, base_delay=0.1, max_delay=1.0)
