"""Tests for Phase 15: Security & Authorization Re-Audit (P12-T01 to P12-T03)."""
import pytest
from core.security.authorization import StudentAuthorizationGuard, SecurityAccessDeniedError


def test_student_authorization_guard_matching_id():
    """Test that matching student IDs pass authorization checks."""
    # Should not raise exception
    StudentAuthorizationGuard.validate_student_access("student_100", "student_100")
    StudentAuthorizationGuard.validate_student_access(" student_200 ", "student_200")


def test_student_authorization_guard_cross_student_blocked():
    """Test that mismatched student IDs raise SecurityAccessDeniedError."""
    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("student_A", "student_B")

    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("", "student_A")

    with pytest.raises(SecurityAccessDeniedError):
        StudentAuthorizationGuard.validate_student_access("student_A", "")


def test_log_sanitization_string():
    """Test string log sanitization for sensitive parameters."""
    raw_log = "User logged in with token=abc123secret and password=my_password"
    cleaned = StudentAuthorizationGuard.sanitize_log_record(raw_log)

    assert "abc123secret" not in cleaned
    assert "my_password" not in cleaned
    assert "token=***REDACTED***" in cleaned
    assert "password=***REDACTED***" in cleaned


def test_log_sanitization_dict():
    """Test dict log sanitization redacting sensitive keys recursively."""
    raw_dict = {
        "user_id": "student_1",
        "api_key": "AIzaSyD_secret_key",
        "nested": {
            "token": "bearer_token_xyz",
            "normal_field": "public_data",
        },
    }
    cleaned = StudentAuthorizationGuard.sanitize_log_record(raw_dict)

    assert cleaned["user_id"] == "student_1"
    assert cleaned["api_key"] == "***REDACTED***"
    assert cleaned["nested"]["token"] == "***REDACTED***"
    assert cleaned["nested"]["normal_field"] == "public_data"
