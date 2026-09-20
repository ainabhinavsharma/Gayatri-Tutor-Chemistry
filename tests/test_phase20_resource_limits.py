"""Tests for Phase 20: Resource & Rate Protection (Section 26).

Verifies:
- Sliding window rate limiter functionality (window expiration, burst limits, retry_after calculation)
- Student and session rate limit isolation (Student A does not block Student B)
- Concurrency guard semaphore preventing parallel overload
- Orchestrator submit() and stream() rate limit handling
- Assessment generation rate limit enforcement
- Multi-threaded concurrency and thread-safety
"""
import concurrent.futures
import time
import pytest

from core.security.rate_limiter import (
    RateLimitExceededError,
    ResourceGovernor,
    SlidingWindowRateLimiter,
    get_governor,
)
from core.orchestrator import Orchestrator, TurnOptions
from core.assessment.manager import AssessmentManager
from core.tutor.state import TutorStateManager


def test_sliding_window_rate_limiter_basic():
    """Verify rate limiter allows requests up to max_requests and rejects subsequent attempts."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_s=2)

    # 3 allowed requests
    limiter.acquire("user_1")
    limiter.acquire("user_1")
    limiter.acquire("user_1")

    assert limiter.is_allowed("user_1") is False
    allowed, retry_after = limiter.check("user_1")
    assert allowed is False
    assert retry_after > 0

    # 4th request raises
    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.acquire("user_1")
    assert "Rate limit of 3 requests per 2s exceeded" in str(exc_info.value)
    assert exc_info.value.retry_after_s > 0

    # Reset clears quota
    limiter.reset("user_1")
    assert limiter.is_allowed("user_1") is True
    limiter.acquire("user_1")


def test_rate_limiter_student_and_session_isolation():
    """Verify Student A exhausting quota does not affect Student B."""
    limiter = SlidingWindowRateLimiter(max_requests=2, window_s=60)

    limiter.acquire("student_a")
    limiter.acquire("student_a")

    # Student A is blocked
    assert limiter.is_allowed("student_a") is False
    with pytest.raises(RateLimitExceededError):
        limiter.acquire("student_a")

    # Student B is completely unaffected
    assert limiter.is_allowed("student_b") is True
    limiter.acquire("student_b")
    limiter.acquire("student_b")
    assert limiter.is_allowed("student_b") is False


def test_concurrency_guard_semaphore():
    """Verify concurrency guard limits parallel execution and rejects over-capacity requests."""
    governor = ResourceGovernor(max_concurrent=2)

    with governor.concurrency_guard():
        with governor.concurrency_guard():
            # 3rd simultaneous acquire with short timeout must fail
            with pytest.raises(RateLimitExceededError, match="maximum concurrent requests"):
                with governor.concurrency_guard(timeout=0.05):
                    pass

    # Once released, new slots can be acquired
    with governor.concurrency_guard():
        pass


def test_orchestrator_submit_rate_limiting():
    """Verify orchestrator submit() rejects requests when turn rate limit is exceeded."""
    governor = get_governor()
    governor.turn_limiter.reset()

    # Artificially lower limit for testing
    governor.turn_limiter.max_requests = 2
    governor.turn_limiter.window_s = 60

    try:
        orch = Orchestrator()
        opts = TurnOptions(student_id="std_rate_1")

        # 1st and 2nd turn succeed
        res1 = orch.submit("What is enthalpy?", session_id="sess_rate_1", options=opts)
        assert res1.status == "SUCCESS"

        res2 = orch.submit("What is entropy?", session_id="sess_rate_1", options=opts)
        assert res2.status == "SUCCESS"

        # 3rd turn rejected by rate limiter
        res3 = orch.submit("What is Gibbs free energy?", session_id="sess_rate_1", options=opts)
        assert res3.status == "ERROR"
        assert res3.routing_reason == "rate_limit_exceeded"
        assert "Rate limit" in res3.text
    finally:
        # Restore default limits
        governor.turn_limiter.max_requests = 30
        governor.turn_limiter.reset()


def test_orchestrator_stream_rate_limiting():
    """Verify orchestrator stream() yields rate limit error and halts when limit exceeded."""
    governor = get_governor()
    governor.turn_limiter.reset()

    governor.turn_limiter.max_requests = 1
    governor.turn_limiter.window_s = 60

    try:
        orch = Orchestrator()
        opts = TurnOptions(student_id="std_stream_rate")

        # First stream succeeds
        tokens1 = list(orch.stream("Explain Hess's Law", session_id="sess_stream_1", options=opts))
        assert any(t[1] is True for t in tokens1)

        # Second stream is rate limited
        tokens2 = list(orch.stream("Explain Hess's Law again", session_id="sess_stream_1", options=opts))
        assert len(tokens2) == 1
        assert tokens2[0][1] is True  # is_last
        assert "Rate limit" in tokens2[0][0]
    finally:
        governor.turn_limiter.max_requests = 30
        governor.turn_limiter.reset()


def test_assessment_manager_rate_limiting(tmp_path):
    """Verify assessment creation enforces rate limits per student."""
    governor = get_governor()
    governor.assessment_limiter.reset()
    governor.assessment_limiter.max_requests = 2
    governor.assessment_limiter.window_s = 60

    state_mgr = TutorStateManager(db_path=tmp_path / "assess_rate.db")
    mgr = AssessmentManager(state_mgr)

    try:
        # 1st and 2nd assessment for student_1 succeed
        id1 = mgr.create_assessment_session("std_assess_1", ["thermo.hess_law"])
        id2 = mgr.create_assessment_session("std_assess_1", ["thermo.hess_law"])
        assert id1 is not None
        assert id2 is not None

        # 3rd assessment for student_1 raises RateLimitExceededError
        with pytest.raises(RateLimitExceededError):
            mgr.create_assessment_session("std_assess_1", ["thermo.hess_law"])

        # Different student can still create assessment
        id_other = mgr.create_assessment_session("std_assess_2", ["thermo.hess_law"])
        assert id_other is not None
    finally:
        governor.assessment_limiter.max_requests = 10
        governor.assessment_limiter.reset()


def test_rate_limiter_thread_safety():
    """Verify rate limiter remains consistent under concurrent multi-threaded access."""
    limiter = SlidingWindowRateLimiter(max_requests=5, window_s=60)
    success_count = 0
    failure_count = 0

    def attempt_acquire():
        nonlocal success_count, failure_count
        try:
            limiter.acquire("shared_key")
            return True
        except RateLimitExceededError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_acquire) for _ in range(10)]
        results = [f.result() for f in futures]

    successes = sum(1 for r in results if r is True)
    failures = sum(1 for r in results if r is False)

    assert successes == 5
    assert failures == 5
