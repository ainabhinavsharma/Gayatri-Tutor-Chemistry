"""Gayatri AI — Student-Isolated Caching Engine (Section 27).

Enforces strict cache isolation across student boundaries:
- Binds all student-sensitive cache keys to 6 identity dimensions:
  1. student_id
  2. concept_id
  3. session_id
  4. query hash (SHA-256)
  5. model version
  6. curriculum version
- Invariant: Student A cached result != Student B result
- Thread-safe storage with TTL support, student-scoped and session-scoped invalidation.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.security.validation import (
    validate_concept_id,
    validate_query_text,
    validate_session_id,
    validate_student_id,
)

logger = logging.getLogger("gayatri.security.cache")


@dataclass(frozen=True)
class StudentCacheKey:
    """Represents a 6-dimensional student-isolated cache key."""
    student_id: str
    concept_id: str
    session_id: str
    query: str
    model_version: str = "default"
    curriculum_version: str = "v1"

    def build_key(self) -> str:
        """Construct the canonical, validated cache key string."""
        clean_student = validate_student_id(self.student_id)
        clean_session = validate_session_id(self.session_id)
        clean_concept = validate_concept_id(self.concept_id)
        clean_query = validate_query_text(self.query)

        clean_mver = str(self.model_version).strip().replace(":", "_").replace(" ", "_")
        clean_cver = str(self.curriculum_version).strip().replace(":", "_").replace(" ", "_")

        qhash = hashlib.sha256(clean_query.encode("utf-8")).hexdigest()

        return (
            f"chem_cache:std={clean_student}:concept={clean_concept}:"
            f"sess={clean_session}:mver={clean_mver}:cver={clean_cver}:qhash={qhash}"
        )


@dataclass
class CacheEntry:
    """Internal cache entry wrapper with expiration and ownership metadata."""
    key: str
    value: Any
    student_id: str
    session_id: str
    created_at: float
    expires_at: Optional[float] = None

    def is_expired(self, now: float) -> bool:
        if self.expires_at is None:
            return False
        return now >= self.expires_at


class IsolatedCacheManager:
    """Thread-safe cache manager guaranteeing cross-student isolation."""

    def __init__(self, default_ttl_s: Optional[int] = None):
        self.default_ttl_s = default_ttl_s
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: StudentCacheKey) -> Optional[Any]:
        """Retrieve a cached value, ensuring strict 6-dimensional identity match and TTL."""
        key_str = key.build_key()
        now = time.time()

        with self._lock:
            entry = self._store.get(key_str)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired(now):
                del self._store[key_str]
                self._misses += 1
                return None

            # Double-check student and session ownership
            if entry.student_id != key.student_id or entry.session_id != key.session_id:
                logger.error(
                    f"CRITICAL: Cache cross-student leakage prevented: entry owner '{entry.student_id}' "
                    f"!= requester '{key.student_id}'"
                )
                del self._store[key_str]
                self._misses += 1
                return None

            self._hits += 1
            return entry.value

    def set(
        self,
        key: StudentCacheKey,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Store a value under the 6-dimensional isolated cache key."""
        key_str = key.build_key()
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_s
        expires_at = (now + ttl) if ttl is not None else None

        with self._lock:
            self._store[key_str] = CacheEntry(
                key=key_str,
                value=value,
                student_id=key.student_id,
                session_id=key.session_id,
                created_at=now,
                expires_at=expires_at,
            )

    def has(self, key: StudentCacheKey) -> bool:
        """Check if an unexpired value exists for the key."""
        return self.get(key) is not None

    def invalidate_student(self, student_id: str) -> int:
        """Evict all cache entries belonging to a student. Returns count of evicted entries."""
        clean_id = validate_student_id(student_id)
        with self._lock:
            keys_to_delete = [
                k for k, entry in self._store.items()
                if entry.student_id == clean_id
            ]
            for k in keys_to_delete:
                del self._store[k]
            logger.info(f"Invalidated {len(keys_to_delete)} cache entries for student '{clean_id}'")
            return len(keys_to_delete)

    def invalidate_session(self, student_id: str, session_id: str) -> int:
        """Evict all cache entries for a specific session. Returns count of evicted entries."""
        clean_student = validate_student_id(student_id)
        clean_session = validate_session_id(session_id)
        with self._lock:
            keys_to_delete = [
                k for k, entry in self._store.items()
                if entry.student_id == clean_student and entry.session_id == clean_session
            ]
            for k in keys_to_delete:
                del self._store[k]
            logger.info(
                f"Invalidated {len(keys_to_delete)} cache entries for student '{clean_student}' "
                f"session '{clean_session}'"
            )
            return len(keys_to_delete)

    def clear(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": (
                    round(self._hits / (self._hits + self._misses), 4)
                    if (self._hits + self._misses) > 0
                    else 0.0
                ),
            }


# Global singleton
_cache_lock = threading.RLock()
_cache_manager: Optional[IsolatedCacheManager] = None


def get_cache_manager() -> IsolatedCacheManager:
    """Get or create the global IsolatedCacheManager singleton."""
    global _cache_manager
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                _cache_manager = IsolatedCacheManager()
    return _cache_manager
