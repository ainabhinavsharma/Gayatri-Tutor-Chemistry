"""Gayatri AI — Learning Dependency Graph.

A directed graph where:
  Nodes   = learning concepts (e.g. "Python Variables", "For Loops")
  Edges   = prerequisite relationships (must know A before B)
  Node attrs = mastery score, exposure count, error count, difficulty

NOT a "mind map" (prior art US20110167329A1, WO2024215244A1).
Called a "Learning Dependency Graph" to avoid patented terminology.

Stored in SQLite. Agents query it to decide what to teach next.
No visual editor — graph is built from curriculum data and updated by agents.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.config import (
    DB_PATH,
    LDG_DECAY_RATE,
    LDG_INITIAL_MASTERY,
    LDG_LEARN_RATE,
    LDG_MASTERY_THRESHOLD,
)

logger = logging.getLogger("gayatri.ldg")


@dataclass
class Concept:
    """A single node in the Learning Dependency Graph."""
    id: str
    name: str
    description: str = ""
    difficulty: float = 0.5
    mastery: float = LDG_INITIAL_MASTERY
    exposure_count: int = 0
    error_count: int = 0
    last_practiced: str = ""
    subject: str = ""
    minimum_mastery: float = 0.85
    evidence_count: int = 3
    assessment_types: list[str] = field(default_factory=list)
    recovery_mode: bool = False
    recovery_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "mastery": self.mastery,
            "exposure_count": self.exposure_count,
            "error_count": self.error_count,
            "last_practiced": self.last_practiced,
            "subject": self.subject,
            "minimum_mastery": self.minimum_mastery,
            "evidence_count": self.evidence_count,
            "assessment_types": self.assessment_types,
            "recovery_mode": self.recovery_mode,
            "recovery_reason": self.recovery_reason,
        }


@dataclass
class Prerequisite:
    """An edge: concept_id requires prereq_id."""
    concept_id: str
    prereq_id: str


class LearningDependencyGraph:
    """Directed graph of learning concepts with mastery tracking.

    Backed by SQLite. Thread-safe for single-user desktop use.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()
        self._cache: dict[str, Concept] = {}
        self._dirty: set[str] = set()

    def _conn(self) -> sqlite3.Connection:
        from core.db import get_safe_db_connection
        return get_safe_db_connection(self.db_path)

    def _create_schema(self) -> None:
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ldg_concepts (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                difficulty      REAL DEFAULT 0.5,
                mastery         REAL DEFAULT 0.3,
                exposure_count  INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                last_practiced  TEXT DEFAULT '',
                subject         TEXT DEFAULT '',
                minimum_mastery REAL DEFAULT 0.85,
                evidence_count  INTEGER DEFAULT 3,
                assessment_types TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS ldg_prerequisites (
                concept_id  TEXT NOT NULL,
                prereq_id   TEXT NOT NULL,
                PRIMARY KEY (concept_id, prereq_id),
                FOREIGN KEY (concept_id) REFERENCES ldg_concepts(id) ON DELETE CASCADE,
                FOREIGN KEY (prereq_id)  REFERENCES ldg_concepts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_ldg_mastery
                ON ldg_concepts(mastery);
            CREATE INDEX IF NOT EXISTS idx_ldg_subject
                ON ldg_concepts(subject);
        """)
        conn.commit()
        conn.close()

    # ── Concept CRUD ─────────────────────────────────────────────────────

    def add_concept(self, concept_id: str, name: str, description: str = "",
                    difficulty: float = 0.5, subject: str = "",
                    minimum_mastery: float = 0.85, evidence_count: int = 3,
                    assessment_types: list[str] | None = None) -> Concept:
        """Add a new concept to the graph. Idempotent — updates if exists."""
        if difficulty < 0.0 or difficulty > 1.0:
            raise ValueError(f"Difficulty must be 0.0-1.0, got {difficulty}")
            
        import json
        assess_str = json.dumps(assessment_types or [])

        conn = self._conn()
        conn.execute(
            """INSERT INTO ldg_concepts (id, name, description, difficulty, subject, minimum_mastery, evidence_count, assessment_types)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   name = excluded.name,
                   description = excluded.description,
                   difficulty = excluded.difficulty,
                   subject = excluded.subject,
                   minimum_mastery = excluded.minimum_mastery,
                   evidence_count = excluded.evidence_count,
                   assessment_types = excluded.assessment_types""",
            (concept_id, name, description, difficulty, subject, minimum_mastery, evidence_count, assess_str),
        )
        conn.commit()
        conn.close()
        logger.info(f"Added concept: {concept_id} ({name})")
        if concept_id in self._cache:
            del self._cache[concept_id]
        return self.get_concept(concept_id)

    def _row_to_concept(self, row) -> Concept:
        import json
        assess_types = []
        try:
            if "assessment_types" in row.keys() and row["assessment_types"]:
                assess_types = json.loads(row["assessment_types"])
        except Exception:
            logger.debug("Failed to parse assessment_types JSON, defaulting to []", exc_info=True)

        return Concept(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            difficulty=row["difficulty"],
            mastery=row["mastery"],
            exposure_count=row["exposure_count"],
            error_count=row["error_count"],
            last_practiced=row["last_practiced"],
            subject=row["subject"],
            minimum_mastery=row["minimum_mastery"] if "minimum_mastery" in row.keys() else 0.85,
            evidence_count=row["evidence_count"] if "evidence_count" in row.keys() else 3,
            assessment_types=assess_types,
        )

    def clear_cache(self) -> None:
        """Clear the in-memory concept cache (Audit #DB-TEST)."""
        self._cache.clear()

    def get_concept(self, concept_id: str) -> Concept | None:
        if concept_id in self._cache:
            return self._cache[concept_id]
        
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM ldg_concepts WHERE id = ?", (concept_id,)
        ).fetchone()
        conn.close()

        if not row:
            return None
            
        concept = self._row_to_concept(row)
        self._cache[concept_id] = concept
        return concept

    def get_all_concepts(self, subject: str = "") -> list[Concept]:
        conn = self._conn()
        if subject:
            rows = conn.execute(
                "SELECT * FROM ldg_concepts WHERE subject = ?", (subject,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM ldg_concepts").fetchall()
        conn.close()
        
        concepts = [self._row_to_concept(row) for row in rows]
        for c in concepts:
            self._cache[c.id] = c
        return concepts

    def list_concepts(self, subject: str = "") -> list[Concept]:
        """List all concepts, optionally filtered by subject."""
        return self.get_all_concepts(subject=subject)

    # ── Prerequisite edges ───────────────────────────────────────────────

    def add_prerequisite(self, concept_id: str, prereq_id: str) -> None:
        """Add a prerequisite edge: concept_id requires prereq_id.

        Idempotent — safe to call multiple times.
        Validates that both concepts exist.
        """
        if concept_id == prereq_id:
            raise ValueError("Concept cannot be its own prerequisite")

        # Ensure both concepts exist
        if self.get_concept(concept_id) is None:
            raise ValueError(f"Concept not found: {concept_id}")
        if self.get_concept(prereq_id) is None:
            raise ValueError(f"Concept not found: {prereq_id}")

        # Check for cycles
        ancestors = set()
        queue = [prereq_id]
        while queue:
            current = queue.pop(0)
            if current == concept_id:
                raise ValueError(f"Adding this prerequisite would create a cycle: {concept_id} requires {prereq_id} which requires {concept_id}")
            for p in self.get_prerequisites(current):
                if p not in ancestors:
                    ancestors.add(p)
                    queue.append(p)

        conn = self._conn()
        conn.execute(
            "INSERT OR IGNORE INTO ldg_prerequisites (concept_id, prereq_id) VALUES (?, ?)",
            (concept_id, prereq_id),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Prerequisite: {concept_id} requires {prereq_id}")

    def get_prerequisites(self, concept_id: str) -> list[str]:
        """Get list of prerequisite concept IDs for a concept."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT prereq_id FROM ldg_prerequisites WHERE concept_id = ?",
            (concept_id,),
        ).fetchall()
        conn.close()
        return [row["prereq_id"] for row in rows]

    def get_dependents(self, concept_id: str) -> list[str]:
        """Get list of concept IDs that depend on this concept."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT concept_id FROM ldg_prerequisites WHERE prereq_id = ?",
            (concept_id,),
        ).fetchall()
        conn.close()
        return [row["concept_id"] for row in rows]

    # ── Mastery tracking ─────────────────────────────────────────────────

    def record_attempt(self, concept_id: str, correct: bool,
                       confidence: float = 1.0) -> float:
        """Record a student's attempt on a concept and update mastery.

        Mastery update (exponential moving average):
          correct: mastery += LEARN_RATE * (1 - mastery) * confidence
          wrong:   mastery -= DECAY_RATE * mastery * confidence

        Args:
            concept_id: The concept being attempted
            correct: Whether the student answered correctly
            confidence: How confident the assessment is (clamped to 0.0-1.0)

        Returns:
            New mastery score
        """
        concept = self.get_concept(concept_id)
        if concept is None:
            raise ValueError(f"Concept not found: {concept_id}")

        # Clamp confidence to [0.0, 1.0] (Audit #35)
        try:
            conf = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            conf = 1.0

        if conf == 0.0:
            # Zero confidence: do not adjust mastery or exposure count
            return concept.mastery
        elif correct:
            # Learn: move mastery toward 1.0
            # Apply slight diminishing return with exposure to prevent oscillation (Audit #36)
            dampening = 1.0 / (1.0 + 0.02 * min(concept.exposure_count, 50))
            delta = LDG_LEARN_RATE * (1.0 - concept.mastery) * conf * dampening
            new_mastery = min(1.0, concept.mastery + delta)
        else:
            # Decay: move mastery toward 0.0
            dampening = 1.0 / (1.0 + 0.02 * min(concept.exposure_count, 50))
            delta = LDG_DECAY_RATE * concept.mastery * conf * dampening
            new_mastery = max(0.0, concept.mastery - delta)

        new_mastery = round(new_mastery, 4)
        old_mastery = concept.mastery
        concept.mastery = new_mastery

        concept.exposure_count += 1
        if not correct:
            concept.error_count += 1
        concept.last_practiced = datetime.now().isoformat()

        # Persist
        conn = self._conn()
        conn.execute(
            """UPDATE ldg_concepts
               SET mastery = ?, exposure_count = ?, error_count = ?, last_practiced = ?
               WHERE id = ?""",
            (concept.mastery, concept.exposure_count, concept.error_count,
             concept.last_practiced, concept_id),
        )
        conn.commit()
        conn.close()

        logger.info(
            f"Attempt {concept_id}: correct={correct}, conf={conf:.2f}, "
            f"mastery={concept.mastery:.3f} (was {old_mastery:.3f})"
        )
        return concept.mastery

    def get_mastery(self, concept_id: str, default: float | None = None) -> float | None:
        """Get current mastery score for a concept (0.0-1.0), or default (None) if untracked."""
        concept = self.get_concept(concept_id)
        if concept is None:
            return default
        return float(concept.mastery)

    def has_concept(self, concept_id: str) -> bool:
        """Check if a concept exists in the graph."""
        return self.get_concept(concept_id) is not None

    def is_unlocked(self, concept_id: str) -> bool:
        """Check if all prerequisites are mastered (>= threshold).

        A concept is unlocked when every existing prerequisite has mastery >= threshold.
        If no prerequisites exist, the concept is always unlocked.
        Missing/orphaned prerequisites are logged and skipped to prevent deadlock (Audit #110).
        """
        prereqs = self.get_prerequisites(concept_id)
        if not prereqs:
            return True
        for p in prereqs:
            mastery = self.get_mastery(p)
            if mastery is None:
                logger.warning(
                    f"Concept '{concept_id}' depends on missing prerequisite '{p}'. "
                    "Skipping missing prerequisite to prevent curriculum deadlock."
                )
                continue
            if mastery < LDG_MASTERY_THRESHOLD:
                return False
        return True

    def is_mastered(self, concept_id: str) -> bool:
        """Check if a concept is mastered (mastery >= LDG_MASTERY_THRESHOLD)."""
        m = self.get_mastery(concept_id)
        return m is not None and m >= LDG_MASTERY_THRESHOLD

    def prune_orphaned_prerequisites(self) -> int:
        """Remove any prerequisite edges referencing non-existent concepts.

        Returns the number of removed orphaned edges (Audit #110).
        """
        conn = self._conn()
        cursor = conn.execute(
            """DELETE FROM ldg_prerequisites
               WHERE concept_id NOT IN (SELECT id FROM ldg_concepts)
                  OR prereq_id NOT IN (SELECT id FROM ldg_concepts)"""
        )
        removed = cursor.rowcount
        conn.commit()
        conn.close()
        if removed > 0:
            logger.info(f"Pruned {removed} orphaned prerequisite edges.")
        return removed

    # ── Learning path ────────────────────────────────────────────────────

    def get_next_concept(self, subject: str = "") -> Concept | None:
        """Get the next concept to teach.

        Selection criteria (in priority order):
          1. Unlocked (all prereqs mastered)
          2. Lowest mastery among unlocked concepts
          3. Lowest difficulty (easier to start)
          4. Least recently practiced

        If no concept is directly unlocked, falls back to the candidate whose
        prerequisites are closest to mastery (Audit #109).
        """
        candidates = self.list_concepts(subject=subject)
        if not candidates:
            return None

        unlocked = [c for c in candidates if self.is_unlocked(c.id)]
        if not unlocked:
            logger.warning(
                f"No concepts directly unlocked for subject='{subject}'. "
                "Selecting candidate closest to unlocking (RECOVERY_MODE)."
            )
            # Fallback: score candidates by how close their prerequisites are to mastery
            def _prereq_mastery_score(cand: Concept) -> tuple[float, float]:
                prereqs = self.get_prerequisites(cand.id)
                existing_prereqs = [p for p in prereqs if self.has_concept(p)]
                if not existing_prereqs:
                    return (1.0, -cand.difficulty)
                scores = [self.get_mastery(p) or 0.0 for p in existing_prereqs]
                avg_m = sum(scores) / len(scores)
                return (avg_m, -cand.difficulty)

            candidates.sort(key=_prereq_mastery_score, reverse=True)
            chosen = candidates[0]
            unmet = [p for p in self.get_prerequisites(chosen.id) if not self.is_mastered(p)]
            unmet_names = [self.get_concept(p).name if self.get_concept(p) else p for p in unmet]
            chosen.recovery_mode = True
            if unmet_names:
                chosen.recovery_reason = (
                    f"Prerequisites not yet mastered: {', '.join(unmet_names)}. "
                    "Focusing on foundational concepts to build understanding."
                )
            else:
                chosen.recovery_reason = "No directly unlocked concepts; initiating recovery review."
            return chosen

        # Sort: lowest mastery first, then lowest difficulty, then oldest practice
        unlocked.sort(key=lambda c: (
            c.mastery,
            c.difficulty,
            -(c.exposure_count),  # prefer concepts not yet practiced
        ))
        return unlocked[0]

    def get_learning_path(self, goal_concept: str) -> list[Concept]:
        """Get the full learning path from roots to a goal concept.

        Uses topological sort on prerequisite edges with cycle detection
        and graceful fallback resolution (Audit #33 & #110).

        Args:
            goal_concept: Target concept ID

        Returns:
            Ordered list of concepts from prerequisites to goal
        """
        all_concepts = {c.id: c for c in self.list_concepts()}
        if goal_concept not in all_concepts:
            return []

        # Collect all ancestors of goal using BFS with visited set
        ancestors = set()
        queue = [goal_concept]
        visited_bfs = {goal_concept}

        while queue:
            current = queue.pop(0)
            prereqs = self.get_prerequisites(current)
            for p in prereqs:
                if p not in all_concepts:
                    # Audit #110: Skip missing prerequisites
                    logger.warning(
                        f"Missing prerequisite '{p}' ignored in learning path for '{goal_concept}'"
                    )
                    continue
                if p not in ancestors:
                    ancestors.add(p)
                if p not in visited_bfs:
                    visited_bfs.add(p)
                    queue.append(p)

        # Kahn's algorithm on the ancestor subgraph
        in_degree = {cid: 0 for cid in ancestors}
        dependents: dict[str, list[str]] = {cid: [] for cid in ancestors}

        for cid in ancestors:
            for prereq in self.get_prerequisites(cid):
                if prereq in ancestors:
                    in_degree[cid] = in_degree.get(cid, 0) + 1
                    dependents[prereq].append(cid)

        # BFS topological sort
        ready_queue = [cid for cid in ancestors if in_degree[cid] == 0]
        sorted_ancestors = []

        while ready_queue:
            ready_queue.sort()  # deterministic order
            node = ready_queue.pop(0)
            sorted_ancestors.append(node)
            for dep in dependents.get(node, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    ready_queue.append(dep)

        # Audit #33: Cycle detection & graceful fallback
        if len(sorted_ancestors) < len(ancestors):
            remaining = [cid for cid in ancestors if cid not in sorted_ancestors]
            logger.warning(
                f"Curriculum cycle detected in learning path for '{goal_concept}'. "
                f"Unresolved cycle nodes: {remaining}. Resolving with fallback topological ordering."
            )
            # Break cycle gracefully by sorting remaining nodes by (in_degree, difficulty, concept_id)
            while remaining:
                remaining.sort(key=lambda cid: (
                    in_degree.get(cid, 0),
                    all_concepts[cid].difficulty if cid in all_concepts else 0.5,
                    cid
                ))
                break_node = remaining.pop(0)
                sorted_ancestors.append(break_node)
                for dep in dependents.get(break_node, []):
                    if dep in in_degree:
                        in_degree[dep] = max(0, in_degree[dep] - 1)

        # Add the goal concept at the end if not already included
        if goal_concept not in sorted_ancestors:
            sorted_ancestors.append(goal_concept)

        return [all_concepts[cid] for cid in sorted_ancestors if cid in all_concepts]

    def get_weak_concepts(self, top_n: int = 5, subject: str = "") -> list[Concept]:
        """Get the concepts with lowest mastery scores.

        Useful for targeted practice and review.
        """
        concepts = self.list_concepts(subject=subject)
        # Sort by mastery ascending, then by exposure (less practiced = more urgent)
        concepts.sort(key=lambda c: (c.mastery, c.exposure_count))
        return concepts[:top_n]

    def get_mastered_concepts(self, subject: str = "") -> list[Concept]:
        """Get concepts where mastery >= threshold."""
        concepts = self.list_concepts(subject=subject)
        return [c for c in concepts if c.mastery >= LDG_MASTERY_THRESHOLD]

    def get_concepts_in_progress(self, subject: str = "") -> list[Concept]:
        """Get concepts with 0 < mastery < threshold."""
        concepts = self.list_concepts(subject=subject)
        return [c for c in concepts if 0.0 < c.mastery < LDG_MASTERY_THRESHOLD]

    def get_not_started_concepts(self, subject: str = "") -> list[Concept]:
        """Get concepts with mastery == initial (never attempted)."""
        concepts = self.list_concepts(subject=subject)
        return [c for c in concepts if c.mastery <= LDG_INITIAL_MASTERY + 0.01]

    def get_progress_stats(self, subject: str = "") -> dict:
        """Get overall progress statistics for a subject."""
        concepts = self.list_concepts(subject=subject)
        if not concepts:
            return {
                "total": 0,
                "mastered": 0,
                "in_progress": 0,
                "not_started": 0,
                "avg_mastery": 0.0,
                "mastery_pct": 0.0,
            }

        mastered = sum(1 for c in concepts if c.mastery >= LDG_MASTERY_THRESHOLD)
        in_progress = sum(1 for c in concepts if 0.0 < c.mastery < LDG_MASTERY_THRESHOLD)
        not_started = sum(1 for c in concepts if c.mastery <= LDG_INITIAL_MASTERY + 0.01)
        avg_mastery = sum(c.mastery for c in concepts) / len(concepts)

        return {
            "total": len(concepts),
            "mastered": mastered,
            "in_progress": in_progress,
            "not_started": not_started,
            "avg_mastery": round(avg_mastery, 3),
            "mastery_pct": round(avg_mastery * 100, 1),
        }

    def reset_concept(self, concept_id: str) -> None:
        """Reset a concept to initial mastery (for retrying)."""
        conn = self._conn()
        conn.execute(
            """UPDATE ldg_concepts
               SET mastery = ?, exposure_count = 0, error_count = 0, last_practiced = ''
               WHERE id = ?""",
            (LDG_INITIAL_MASTERY, concept_id),
        )
        conn.commit()
        conn.close()
        if concept_id in self._cache:
            del self._cache[concept_id]
        logger.info(f"Reset concept: {concept_id}")

    def reset_all(self) -> None:
        """Reset all concepts to initial mastery. Use with caution."""
        conn = self._conn()
        conn.execute(
            """UPDATE ldg_concepts
               SET mastery = ?, exposure_count = 0, error_count = 0, last_practiced = ''
            """,
            (LDG_INITIAL_MASTERY,),
        )
        conn.commit()
        conn.close()
        self.clear_cache()
        logger.warning("Reset ALL concepts to initial mastery.")

    def delete_concept(self, concept_id: str) -> None:
        """Remove a concept and its prerequisite edges."""
        conn = self._conn()
        conn.execute("DELETE FROM ldg_prerequisites WHERE concept_id = ? OR prereq_id = ?",
                     (concept_id, concept_id))
        conn.execute("DELETE FROM ldg_concepts WHERE id = ?", (concept_id,))
        conn.commit()
        conn.close()
        if concept_id in self._cache:
            del self._cache[concept_id]
        logger.info(f"Deleted concept: {concept_id}")


# ── Curriculum loader ────────────────────────────────────────────────────

def load_curriculum(graph: LearningDependencyGraph, curriculum_path: str | Path) -> int:
    from core.curriculum.loader import load_curriculum as _load
    return _load(graph, curriculum_path)


def get_ldg(db_path: str | Path | None = None) -> LearningDependencyGraph:
    """Get the active LearningDependencyGraph instance."""
    try:
        from core.orchestrator import _get_ldg
        ldg = _get_ldg()
        if ldg is not None and db_path is None:
            return ldg
    except Exception:
        logger.debug("Could not reuse existing LDG, creating new instance", exc_info=True)
    return LearningDependencyGraph(db_path=db_path)

