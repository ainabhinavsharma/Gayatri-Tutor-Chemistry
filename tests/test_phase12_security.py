"""Phase 12 Test Suite: Security and Data Isolation.

Verifies student authorization guards, cross-student data isolation,
and log credential sanitization (P12-T01 through P12-T03).
"""
import pytest
from core.security.authorization import SecurityAccessDeniedError, StudentAuthorizationGuard


def test_student_authorization_guard_same_student():
    # Matching student ID -> access granted
    StudentAuthorizationGuard.validate_student_access("student_A", "student_A")


def test_student_authorization_guard_cross_student_blocked():
    # Student A attempting to access Student B's data -> blocked
    with pytest.raises(SecurityAccessDeniedError) as exc_info:
        StudentAuthorizationGuard.validate_student_access("student_A", "student_B")

    assert "Cross-student access blocked" in str(exc_info.value)


def test_log_sanitization_dict():
    raw = {
        "user_id": "student_1",
        "api_key": "secret_key_12345",
        "password": "my_password",
        "nested": {"token": "bearer_abc_789"},
    }

    sanitized = StudentAuthorizationGuard.sanitize_log_record(raw)
    assert sanitized["user_id"] == "student_1"
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["nested"]["token"] == "***REDACTED***"


def test_log_sanitization_string():
    raw_str = "Login attempt with password=supersecret and token=12345"
    sanitized_str = StudentAuthorizationGuard.sanitize_log_record(raw_str)
    assert "password=***REDACTED***" in sanitized_str
    assert "token=***REDACTED***" in sanitized_str
