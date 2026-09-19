"""Student Data Isolation and Security Guard (Phase 12).

Enforces strict student ID authorization, session ownership validation,
and log data sanitization to prevent data leakage (P12-T01 through P12-T03).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Union


class SecurityAccessDeniedError(PermissionError):
    """Raised when cross-student authorization fails."""
    pass


class StudentAuthorizationGuard:
    """Security guard for student data isolation and log sanitization."""

    SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "credentials", "bearer", "auth_token"}

    @classmethod
    def validate_student_access(cls, requesting_student_id: str, target_student_id: str) -> None:
        """Enforce strict student ID match (P12-T01 & P12-T02)."""
        if not requesting_student_id or not target_student_id:
            raise SecurityAccessDeniedError("Invalid student ID in authorization check.")

        if requesting_student_id.strip() != target_student_id.strip():
            raise SecurityAccessDeniedError(
                f"Cross-student access blocked: '{requesting_student_id}' requested data for '{target_student_id}'."
            )

    @classmethod
    def sanitize_log_record(cls, record: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Sanitize sensitive credentials, tokens, and passwords from logs (P12-T03)."""
        if isinstance(record, str):
            # Mask pattern matches like token=xyz or bearer xyz
            cleaned = re.sub(r'(?i)(token|bearer|password|api_key|secret)=[\w\-]+', r'\1=***REDACTED***', record)
            return cleaned

        if isinstance(record, dict):
            cleaned_dict = {}
            for k, v in record.items():
                if k.lower() in cls.SENSITIVE_KEYS:
                    cleaned_dict[k] = "***REDACTED***"
                elif isinstance(v, dict):
                    cleaned_dict[k] = cls.sanitize_log_record(v)
                elif isinstance(v, str):
                    cleaned_dict[k] = cls.sanitize_log_record(v)
                else:
                    cleaned_dict[k] = v
            return cleaned_dict

        return record
