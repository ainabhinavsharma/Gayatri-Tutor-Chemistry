"""Gayatri AI — Resource & Rate Protection (Section 26).

Protects LLM calls, RAG, file processing, assessment generation, and streaming endpoints:
- Sliding window rate limiting per student, session, and operation
- Concurrency limiting using semaphores
- Operation timeouts (LLM, RAG, Assessment)
- Context and response size guards
- Prevent one user or session from exhausting system resources or API quotas.
"""
from __future__ import annotations

import collections
import contextlib
import logging
import threading
import time
from typing import Dict, Iterator, Optional, Tuple

from core.config import (
    AGENT_TIMEOUT_S,
    MAX_CONCURRENT_REQUESTS,
    MAX_INPUT_CHARS,
    RATE_LIMIT_REQUESTS_PER_MIN,
    RATE_LIMIT_WINDOW_S,
)

logger = logging.getLogger("gayatri.security.rate_limiter")


class RateLimitExceededError(Exception):
    """Raised when an operation exceeds its configured rate limit."""

    def __init__(
        self,
        message: str,
        key: str = "",
        limit: int = 0,
        window_s: int = 0,
        retry_after_s: int = 0,
    ):
        super().__init__(message)
        self.key = key
        self.limit = limit
        self.window_s = window_s
        self.retry_after_s = retry_after_s


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(
        self,
        max_requests: int = RATE_LIMIT_REQUESTS_PER_MIN,
        window_s: int = RATE_LIMIT_WINDOW_S,
    ):
        self.max_requests = max_requests
        self.window_s = window_s
        self._lock = threading.RLock()
        self._timestamps: Dict[str, collections.deque] = collections.defaultdict(collections.deque)

    def _prune(self, key: str, now: float) -> collections.deque:
        """Remove timestamps older than the current sliding window."""
        window_start = now - self.window_s
        dq = self._timestamps[key]
        while dq and dq[0] <= window_start:
            dq.popleft()
        return dq

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed without consuming quota or raising."""
        allowed, _ = self.check(key)
        return allowed

    def check(self, key: str) -> Tuple[bool, int]:
        """Check rate limit for key.

        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        with self._lock:
            dq = self._prune(key, now)
            if len(dq) < self.max_requests:
                return True, 0

            # Calculate retry after based on oldest timestamp in window
            oldest = dq[0] if dq else now
            retry_after = max(1, int((oldest + self.window_s) - now) + 1)
            return False, retry_after

    def acquire(self, key: str) -> None:
        """Acquire a slot in the rate limit window.

        Raises RateLimitExceededError if limit is reached.
        """
        now = time.time()
        with self._lock:
            dq = self._prune(key, now)
            if len(dq) >= self.max_requests:
                oldest = dq[0] if dq else now
                retry_after = max(1, int((oldest + self.window_s) - now) + 1)
                logger.warning(
                    f"Rate limit exceeded for key '{key}': {len(dq)}/{self.max_requests} "
                    f"requests in {self.window_s}s window. Retry after {retry_after}s."
                )
                raise RateLimitExceededError(
                    f"Rate limit of {self.max_requests} requests per {self.window_s}s exceeded. "
                    f"Please wait {retry_after} seconds before trying again.",
                    key=key,
                    limit=self.max_requests,
                    window_s=self.window_s,
                    retry_after_s=retry_after,
                )

            dq.append(now)

    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limit history for a specific key or all keys."""
        with self._lock:
            if key is not None:
                self._timestamps.pop(key, None)
            else:
                self._timestamps.clear()


class ResourceGovernor:
    """Central manager for rate limits, concurrency caps, and timeouts."""

    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
        turn_rate_limit: int = RATE_LIMIT_REQUESTS_PER_MIN,
        turn_window_s: int = RATE_LIMIT_WINDOW_S,
        assessment_limit: int = 10,
        assessment_window_s: int = 60,
        rag_limit: int = 60,
        rag_window_s: int = 60,
    ):
        self._semaphore = threading.BoundedSemaphore(max_concurrent)
        self.turn_limiter = SlidingWindowRateLimiter(turn_rate_limit, turn_window_s)
        self.assessment_limiter = SlidingWindowRateLimiter(assessment_limit, assessment_window_s)
        self.rag_limiter = SlidingWindowRateLimiter(rag_limit, rag_window_s)

        self._timeouts = {
            "llm": float(AGENT_TIMEOUT_S),
            "rag": 10.0,
            "assessment": 30.0,
            "upload": 15.0,
        }

    def check_turn(self, student_id: str, session_id: str) -> None:
        """Check and acquire rate limit quota for a user turn.

        Enforces dual limits: per-student and per-session.
        """
        if student_id:
            self.turn_limiter.acquire(f"student:{student_id}")
        if session_id:
            self.turn_limiter.acquire(f"session:{session_id}")

    def check_assessment(self, student_id: str) -> None:
        """Check and acquire rate limit quota for assessment generation."""
        clean_id = student_id or "default"
        self.assessment_limiter.acquire(f"assessment:{clean_id}")

    def check_rag(self, student_id: str) -> None:
        """Check and acquire rate limit quota for RAG retrieval."""
        clean_id = student_id or "default"
        self.rag_limiter.acquire(f"rag:{clean_id}")

    @contextlib.contextmanager
    def concurrency_guard(self, timeout: float = 5.0) -> Iterator[None]:
        """Acquire a concurrency slot to protect CPU/GPU from parallel overload."""
        acquired = self._semaphore.acquire(timeout=timeout)
        if not acquired:
            logger.warning("ResourceGovernor: concurrency limit reached, operation rejected or timed out")
            raise RateLimitExceededError(
                "The system is currently handling maximum concurrent requests. Please try again shortly.",
                key="concurrency",
                retry_after_s=3,
            )
        try:
            yield
        finally:
            self._semaphore.release()

    def timeout_for(self, operation: str) -> float:
        """Get the configured timeout for an operation in seconds."""
        return self._timeouts.get(operation, 30.0)

    def reset(self) -> None:
        """Reset all rate limiters."""
        self.turn_limiter.reset()
        self.assessment_limiter.reset()
        self.rag_limiter.reset()


# Global singleton
_governor_lock = threading.RLock()
_governor: Optional[ResourceGovernor] = None


def get_governor() -> ResourceGovernor:
    """Get or create the global ResourceGovernor singleton."""
    global _governor
    if _governor is None:
        with _governor_lock:
            if _governor is None:
                _governor = ResourceGovernor()
    return _governor
