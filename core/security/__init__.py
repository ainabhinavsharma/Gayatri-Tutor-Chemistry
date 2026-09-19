"""
Core Security package (Phase 12).
Provides secret management, cryptographic signature verification,
student authorization guards, and log sanitization.
"""
from core.security.authorization import StudentAuthorizationGuard, SecurityAccessDeniedError

__all__ = [
    "StudentAuthorizationGuard",
    "SecurityAccessDeniedError",
]
