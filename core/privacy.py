"""Gayatri AI — PII Detection and Redaction.

Simple regex-based PII scanner. Replaces personal data with safe placeholders
before messages reach the model. User sees original text; model sees [PII_TYPE].

Avoids Samsung's patented "dummy placeholder substitution" approach
(US patent 2026 by Samsung for on-device AI privacy).
This is a simple, non-patented regex replacement with restore capability.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger("gayatri.privacy")

# Verhoeff algorithm tables for Aadhaar checksum validation (Audit #94)
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def validate_verhoeff(num_str: str) -> bool:
    """Validate 12-digit Indian Aadhaar number using Verhoeff checksum algorithm (Audit #94)."""
    digits = [c for c in num_str if c.isdigit()]
    if len(digits) != 12 or digits[0] in ("0", "1"):
        return False
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def validate_luhn(num_str: str) -> bool:
    """Validate payment card number using Luhn algorithm (Audit #95)."""
    digits = [int(c) for c in num_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled if doubled < 10 else doubled - 9
        else:
            checksum += digit
    return checksum % 10 == 0


@dataclass
class PIIMatch:
    """A single PII match."""
    pii_type: str
    placeholder: str
    original: str
    start: int
    end: int


@dataclass
class RedactionResult:
    """Result of redacting a message."""
    clean_text: str
    redactions: list[PIIMatch] = field(default_factory=list)
    has_pii: bool = False

    def restore(self, text: str) -> str:
        """Restore original PII in the clean text (for display)."""
        result = text
        for r in self.redactions:
            result = result.replace(r.placeholder, r.original)
        return result


class PIIRedactor:
    """Simple regex-based PII detector and redactor with checksum verification.

    Detects:
        - Email addresses
        - UPI IDs (Indian Virtual Payment Addresses, e.g. user@oksbi, student@paytm)
        - Credit/debit cards (with Luhn checksum validation)
        - Aadhaar numbers (12 digits with Verhoeff checksum validation)
        - PAN cards (Indian Permanent Account Number)
        - Indian passports
        - Indian phone numbers (10 digits starting with 6-9, optional +91)
        - US/generic phone numbers (xxx-xxx-xxxx)
        - SSN-like numbers (xxx-xx-xxxx)

    Safe approach: regex replacement + restore via placeholder map.
    Does NOT implement Samsung's patented placeholder masking technique.
    """

    PATTERNS: list[tuple[str, re.Pattern, Callable[[str], bool] | None]] = [
        ("EMAIL", re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ), None),
        ("UPI_ID", re.compile(
            r"\b[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z0-9]{2,32}\b"
        ), None),
        ("CREDIT_CARD", re.compile(
            r"\b(?:\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|\d{4}[\s-]?\d{6}[\s-]?\d{5}|\d{13,19})\b"
        ), validate_luhn),
        ("AADHAAR", re.compile(
            r"(?<!\d)[2-9]\d{3}[\s-]?(?:\d{4}[\s-]?\d{4}|\d{8})(?!\d)"
        ), validate_verhoeff),
        ("PAN", re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
        ), None),
        ("PASSPORT_IN", re.compile(
            r"\b[A-Z][0-9]{7}\b"
        ), None),
        ("PHONE_IN", re.compile(
            r"(?<!\d)(?:\+?91[-\s.]?)?[6-9]\d{9}(?!\d)"
        ), None),
        ("PHONE_US", re.compile(
            r"\b\d{3}[-\s.]\d{3}[-\s.]\d{4}\b"
        ), None),
        ("SSN", re.compile(
            r"\b\d{3}-\d{2}-\d{4}\b"
        ), None),
    ]

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def redact(self, text: str) -> RedactionResult:
        """Scan text and replace PII with placeholders.

        Args:
            text: Original text potentially containing PII

        Returns:
            RedactionResult with clean_text and redactions list
        """
        if not self.enabled or not text:
            return RedactionResult(clean_text=text, has_pii=False)

        import secrets
        run_id = secrets.token_hex(4)
        matches: list[PIIMatch] = []
        result_text = text

        for entry in self.PATTERNS:
            if len(entry) == 3:
                pii_type, pattern, validator = entry
            else:
                pii_type, pattern = entry
                validator = None

            def replacer(match: re.Match) -> str:
                original = match.group(0)
                if validator is not None and not validator(original):
                    return original
                idx = len(matches)
                placeholder = f"[{pii_type}_{idx}_{run_id}]"
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    placeholder=placeholder,
                    original=original,
                    start=match.start(),
                    end=match.end(),
                ))
                return placeholder

            result_text = pattern.sub(replacer, result_text)

        return RedactionResult(
            clean_text=result_text,
            redactions=matches,
            has_pii=len(matches) > 0,
        )

    def get_redaction_summary(self, result: RedactionResult) -> str:
        """Get a human-readable summary of what was redacted."""
        if not result.has_pii:
            return "No PII detected"
        types = {}
        for r in result.redactions:
            types[r.pii_type] = types.get(r.pii_type, 0) + 1
        parts = [f"{count} {ptype}" for ptype, count in types.items()]
        return "Redacted: " + ", ".join(parts)


# Global redactor instance
_redactor: PIIRedactor | None = None


def get_redactor() -> PIIRedactor:
    """Get the global PII redactor (singleton)."""
    global _redactor
    if _redactor is None:
        _redactor = PIIRedactor(enabled=True)
    return _redactor
