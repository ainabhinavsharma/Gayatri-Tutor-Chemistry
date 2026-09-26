
import logging
import time
from datetime import datetime

from core.tutor_engine import TutorEngine

logger = logging.getLogger('gayatri.tutor.decay')

class MasteryDecayScheduler:
    def __init__(self, ldg, tutor_engine: TutorEngine):
        self.ldg = ldg
        self.tutor_engine = tutor_engine
        # Decay half-life in seconds (e.g., 7 days)
        self.half_life_s = 7 * 24 * 3600

    def apply_decay_and_queue(self, session_id: str):
        ctx = self.tutor_engine.get_or_create_context(session_id)

        # We need to iterate over all concepts in the subject
        # For simplicity, we just fetch all concepts from DB
        conn = self.ldg._conn()
        decayed_any = False
        try:
            with conn:
                cursor = conn.execute(
                    'SELECT id, mastery, last_practiced FROM ldg_concepts WHERE subject = ? COLLATE NOCASE AND mastery >= 0.4',
                    (ctx.subject or "Chemistry",)
                )
                rows = cursor.fetchall()
                now = time.time()

                for row in rows:
                    concept_id, mastery, last_practiced_str = row
                    if not last_practiced_str:
                        continue

                    try:
                        # Parse ISO timestamp
                        last_dt = datetime.fromisoformat(last_practiced_str)
                        last_ts = last_dt.timestamp()
                    except ValueError:
                        continue

                    elapsed = now - last_ts
                    if elapsed > 0:
                        # Exponential decay formula: N(t) = N0 * (0.5) ^ (t / t_half)
                        # But we don't want it to decay below 0.3 (baseline)
                        baseline = 0.3
                        decay_factor = (0.5) ** (elapsed / self.half_life_s)
                        new_mastery = baseline + (mastery - baseline) * decay_factor

                        # If it dropped a level (e.g., went below 0.9 or 0.7), add to review queue
                        from core.tutor_engine import mastery_level
                        old_level = mastery_level(mastery)
                        new_level = mastery_level(new_mastery)

                        if new_level != old_level and new_mastery < 0.9:
                            if concept_id not in ctx.review_queue:
                                ctx.review_queue.append(concept_id)

                        conn.execute(
                            'UPDATE ldg_concepts SET mastery = ? WHERE id = ?',
                            (new_mastery, concept_id)
                        )
                        decayed_any = True
        finally:
            conn.close()

        if decayed_any:
            self.tutor_engine.save_context(session_id)

