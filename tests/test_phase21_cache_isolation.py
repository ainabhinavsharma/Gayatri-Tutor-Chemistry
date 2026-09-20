"""Tests for Phase 21: Cache Isolation (Section 27).

Verifies:
- Mandatory Section 27 test: Student A cached result != Student B result
- 6-dimensional identity binding: student_id, concept_id, session_id, query hash, model_version, curriculum_version
- Cache miss when any of the 6 dimensions change
- Zero-trust key validation (path traversal, null bytes, empty strings)
- Student-scoped and session-scoped invalidation
- TTL expiration
- Thread safety under concurrent access
"""
import concurrent.futures
import time
import pytest

from core.security.cache import (
    IsolatedCacheManager,
    StudentCacheKey,
    get_cache_manager,
)


@pytest.fixture
def cache():
    """Provide a clean IsolatedCacheManager instance."""
    return IsolatedCacheManager()


def test_mandatory_cross_student_isolation(cache):
    """Verify Section 27 mandatory invariant: Student A cached result != Student B result."""
    key_a = StudentCacheKey(
        student_id="student_a",
        concept_id="thermo.enthalpy",
        session_id="sess_1",
        query="What is enthalpy?",
        model_version="local_v1",
        curriculum_version="cbse_chem_11",
    )
    key_b = StudentCacheKey(
        student_id="student_b",
        concept_id="thermo.enthalpy",
        session_id="sess_1",
        query="What is enthalpy?",
        model_version="local_v1",
        curriculum_version="cbse_chem_11",
    )

    # Cache Student A's result
    cache.set(key_a, "Enthalpy is the sum of internal energy and pressure-volume product for Student A.")

    # Student B queries the EXACT same question, concept, session, and versions
    # MUST result in a cache miss
    assert cache.get(key_b) is None
    assert cache.has(key_b) is False

    # Cache Student B's result with their own data
    cache.set(key_b, "Enthalpy explanation customized for Student B.")

    # Invariant verified: Student A cached result != Student B result
    result_a = cache.get(key_a)
    result_b = cache.get(key_b)
    assert result_a != result_b
    assert "Student A" in result_a
    assert "Student B" in result_b


def test_six_dimensional_identity_sensitivity(cache):
    """Verify cache miss occurs whenever ANY of the 6 identity dimensions change."""
    base_key = StudentCacheKey(
        student_id="std_101",
        concept_id="thermo.first_law",
        session_id="session_alpha",
        query="State the first law of thermodynamics",
        model_version="model_2026",
        curriculum_version="ncert_v2",
    )
    cache.set(base_key, "Energy cannot be created or destroyed.")
    assert cache.get(base_key) == "Energy cannot be created or destroyed."

    # 1. Different student_id
    diff_student = StudentCacheKey(
        student_id="std_102",
        concept_id=base_key.concept_id,
        session_id=base_key.session_id,
        query=base_key.query,
        model_version=base_key.model_version,
        curriculum_version=base_key.curriculum_version,
    )
    assert cache.get(diff_student) is None

    # 2. Different concept_id
    diff_concept = StudentCacheKey(
        student_id=base_key.student_id,
        concept_id="thermo.second_law",
        session_id=base_key.session_id,
        query=base_key.query,
        model_version=base_key.model_version,
        curriculum_version=base_key.curriculum_version,
    )
    assert cache.get(diff_concept) is None

    # 3. Different session_id
    diff_session = StudentCacheKey(
        student_id=base_key.student_id,
        concept_id=base_key.concept_id,
        session_id="session_beta",
        query=base_key.query,
        model_version=base_key.model_version,
        curriculum_version=base_key.curriculum_version,
    )
    assert cache.get(diff_session) is None

    # 4. Different query (query hash)
    diff_query = StudentCacheKey(
        student_id=base_key.student_id,
        concept_id=base_key.concept_id,
        session_id=base_key.session_id,
        query="Give mathematical expression for first law",
        model_version=base_key.model_version,
        curriculum_version=base_key.curriculum_version,
    )
    assert cache.get(diff_query) is None

    # 5. Different model_version
    diff_model = StudentCacheKey(
        student_id=base_key.student_id,
        concept_id=base_key.concept_id,
        session_id=base_key.session_id,
        query=base_key.query,
        model_version="model_2027_updated",
        curriculum_version=base_key.curriculum_version,
    )
    assert cache.get(diff_model) is None

    # 6. Different curriculum_version
    diff_curriculum = StudentCacheKey(
        student_id=base_key.student_id,
        concept_id=base_key.concept_id,
        session_id=base_key.session_id,
        query=base_key.query,
        model_version=base_key.model_version,
        curriculum_version="ncert_v3_revised",
    )
    assert cache.get(diff_curriculum) is None


def test_key_validation_enforcement():
    """Verify cache keys enforce zero-trust validation on all identifiers."""
    # Path traversal in student_id
    with pytest.raises(ValueError, match="path traversal or null byte"):
        StudentCacheKey(
            student_id="../evil_student",
            concept_id="thermo.enthalpy",
            session_id="sess_1",
            query="test",
        ).build_key()

    # Path traversal in session_id
    with pytest.raises(ValueError, match="path traversal or null byte"):
        StudentCacheKey(
            student_id="student_1",
            concept_id="thermo.enthalpy",
            session_id="../../evil_sess",
            query="test",
        ).build_key()

    # Path traversal in concept_id
    with pytest.raises(ValueError, match="path traversal or null byte"):
        StudentCacheKey(
            student_id="student_1",
            concept_id="../evil_concept",
            session_id="sess_1",
            query="test",
        ).build_key()

    # Empty query
    with pytest.raises(ValueError, match="Query text must not be empty"):
        StudentCacheKey(
            student_id="student_1",
            concept_id="thermo.enthalpy",
            session_id="sess_1",
            query="   ",
        ).build_key()


def test_student_and_session_invalidation(cache):
    """Verify student-scoped and session-scoped invalidation removes only targeted entries."""
    # Student A: 2 sessions
    k_a_s1_1 = StudentCacheKey("std_a", "c1", "s1", "q1")
    k_a_s1_2 = StudentCacheKey("std_a", "c2", "s1", "q2")
    k_a_s2_1 = StudentCacheKey("std_a", "c1", "s2", "q3")

    # Student B: 1 session
    k_b_s1_1 = StudentCacheKey("std_b", "c1", "s1", "q4")
    k_b_s1_2 = StudentCacheKey("std_b", "c2", "s1", "q5")

    cache.set(k_a_s1_1, "A-s1-1")
    cache.set(k_a_s1_2, "A-s1-2")
    cache.set(k_a_s2_1, "A-s2-1")
    cache.set(k_b_s1_1, "B-s1-1")
    cache.set(k_b_s1_2, "B-s1-2")

    assert cache.stats()["size"] == 5

    # Invalidate Student A, session s1 only
    evicted = cache.invalidate_session("std_a", "s1")
    assert evicted == 2
    assert cache.get(k_a_s1_1) is None
    assert cache.get(k_a_s1_2) is None
    assert cache.get(k_a_s2_1) == "A-s2-1"  # session s2 still present

    # Student B entries are completely unaffected
    assert cache.get(k_b_s1_1) == "B-s1-1"
    assert cache.get(k_b_s1_2) == "B-s1-2"

    # Invalidate all remaining entries for Student A
    evicted_a = cache.invalidate_student("std_a")
    assert evicted_a == 1
    assert cache.get(k_a_s2_1) is None

    # Student B entries STILL unaffected
    assert cache.get(k_b_s1_1) == "B-s1-1"
    assert cache.get(k_b_s1_2) == "B-s1-2"
    assert cache.stats()["size"] == 2


def test_ttl_expiration(cache):
    """Verify entries expire and are cleaned up after TTL passes."""
    key = StudentCacheKey("std_ttl", "thermo.gibbs", "sess_ttl", "What is delta G?")
    cache.set(key, "delta G = delta H - T delta S", ttl_seconds=1)

    assert cache.get(key) is not None

    # Sleep past expiration
    time.sleep(1.1)

    # Must be expired
    assert cache.get(key) is None
    assert cache.has(key) is False


def test_thread_safety_under_concurrency(cache):
    """Verify thread-safe read/write operations across multiple students in parallel."""
    def worker(student_idx: int):
        std_id = f"std_conc_{student_idx}"
        key = StudentCacheKey(
            student_id=std_id,
            concept_id="thermo.hess_law",
            session_id=f"sess_{student_idx}",
            query=f"Query from student {student_idx}",
        )
        cache.set(key, f"Result_{student_idx}")
        val = cache.get(key)
        return val == f"Result_{student_idx}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(20)]
        results = [f.result() for f in futures]

    assert all(results)
    assert cache.stats()["size"] == 20
