"""Gayatri AI — Zero-Trust Input Validation (Section 24).

Validates all external and client-supplied inputs across application boundaries:
- Student IDs, Session IDs, Concept IDs, Question IDs
- Query and prompt lengths
- JSON structures and size limits
- File types, extensions, sizes, and MIME signatures

Invariant: Never trust client-supplied input, filenames, Content-Types, or identifiers.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, List, Optional, Set, Union

logger = logging.getLogger("gayatri.security.validation")

# ── Identifier Patterns ───────────────────────────────────────────────
_STUDENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\.\-@]{1,64}$")
_SESSION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-:]{1,128}$")
_CONCEPT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_.\-]{1,128}$")
_QUESTION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_.\-]{1,128}$")

# ── Length & Size Defaults ────────────────────────────────────────────
DEFAULT_MAX_QUERY_LENGTH = 4000
DEFAULT_MAX_PROMPT_LENGTH = 32000
DEFAULT_MAX_JSON_BYTES = 1_000_000       # 1 MB
DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

# ── Allowed Document Extensions ───────────────────────────────────────
ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf",
    ".txt",
    ".json",
    ".csv",
    ".md",
}

# Dangerous executable extensions that must never be permitted
DISALLOWED_EXECUTABLE_EXTENSIONS: Set[str] = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".ps1", ".vbs", ".js", ".py", ".msi", ".dll",
    ".php", ".jsp", ".asp", ".cgi", ".phtml", ".phar"
}


def validate_student_id(student_id: str) -> str:
    """Validate student ID against strict alphanumeric + safe delimiter rules.

    Rejects path traversal, null bytes, command injection, and SQL injection characters.
    """
    if not isinstance(student_id, str):
        raise ValueError(f"Student ID must be a string, got {type(student_id).__name__}")

    cleaned = student_id.strip()
    if not cleaned:
        raise ValueError("student_id must not be empty")
    if len(cleaned) > 64:
        raise ValueError(f"Student ID length must be between 1 and 64 characters (got {len(cleaned)})")

    if "\x00" in cleaned or ".." in cleaned:
        raise ValueError(f"Student ID contains forbidden path traversal or null byte: '{cleaned}'")

    if not _STUDENT_ID_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid student ID '{cleaned}': must contain only alphanumeric characters, "
            "underscores, hyphens, periods, or '@' without spaces or shell characters."
        )

    return cleaned


def validate_session_id(session_id: str) -> str:
    """Validate session ID against strict security criteria.

    Prevents path traversal ('../'), command injection, control characters,
    and null bytes at the persistence boundary.
    """
    if not isinstance(session_id, str):
        raise ValueError(f"Session ID must be a string, got {type(session_id).__name__}")

    cleaned = session_id.strip()
    if not cleaned or len(cleaned) > 128:
        raise ValueError(f"Session ID length must be between 1 and 128 characters (got {len(cleaned)})")

    if "\x00" in cleaned or ".." in cleaned:
        raise ValueError(f"Session ID contains forbidden path traversal or null byte: '{cleaned}'")

    if not _SESSION_ID_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid session ID '{cleaned}': must contain only 1-128 alphanumeric characters, "
            "underscores, hyphens, and colons without path traversal characters."
        )

    return cleaned


def validate_concept_id(concept_id: str) -> str:
    """Validate concept ID against stable programmatic ID pattern (e.g., 'chem.thermo.enthalpy')."""
    if not isinstance(concept_id, str):
        raise ValueError(f"Concept ID must be a string, got {type(concept_id).__name__}")

    cleaned = concept_id.strip()
    if not cleaned or len(cleaned) > 128:
        raise ValueError(f"Concept ID length must be between 1 and 128 characters (got {len(cleaned)})")

    if "\x00" in cleaned or ".." in cleaned:
        raise ValueError(f"Concept ID contains forbidden path traversal or null byte: '{cleaned}'")

    if not _CONCEPT_ID_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid concept ID '{cleaned}': must match programmatic pattern '^[a-zA-Z0-9_.\\-]{{1,128}}$'."
        )

    return cleaned


def validate_question_id(question_id: str) -> str:
    """Validate question ID against programmatic ID rules."""
    if not isinstance(question_id, str):
        raise ValueError(f"Question ID must be a string, got {type(question_id).__name__}")

    cleaned = question_id.strip()
    if not cleaned or len(cleaned) > 128:
        raise ValueError(f"Question ID length must be between 1 and 128 characters (got {len(cleaned)})")

    if "\x00" in cleaned or ".." in cleaned:
        raise ValueError(f"Question ID contains forbidden path traversal or null byte: '{cleaned}'")

    if not _QUESTION_ID_REGEX.match(cleaned):
        raise ValueError(
            f"Invalid question ID '{cleaned}': must match programmatic pattern '^[a-zA-Z0-9_.\\-]{{1,128}}$'."
        )

    return cleaned


def validate_query_text(query: str, max_length: int = DEFAULT_MAX_QUERY_LENGTH) -> str:
    """Validate user query text for length and null bytes."""
    if not isinstance(query, str):
        raise ValueError(f"Query text must be a string, got {type(query).__name__}")

    if "\x00" in query:
        raise ValueError("Query text contains forbidden null bytes (\\x00)")

    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Query text must not be empty")

    if len(cleaned) > max_length:
        raise ValueError(
            f"Query text exceeds maximum allowed length of {max_length} characters (got {len(cleaned)})"
        )

    return cleaned


def validate_prompt_text(prompt: str, max_length: int = DEFAULT_MAX_PROMPT_LENGTH) -> str:
    """Validate prompt text length and null bytes."""
    if not isinstance(prompt, str):
        raise ValueError(f"Prompt text must be a string, got {type(prompt).__name__}")

    if "\x00" in prompt:
        raise ValueError("Prompt text contains forbidden null bytes (\\x00)")

    if len(prompt) > max_length:
        raise ValueError(
            f"Prompt text exceeds maximum allowed length of {max_length} characters (got {len(prompt)})"
        )

    return prompt


def validate_json(
    raw_json: Union[str, bytes],
    max_size_bytes: int = DEFAULT_MAX_JSON_BYTES,
    required_keys: Optional[List[str]] = None,
    max_bytes: Optional[int] = None,
) -> Union[dict, list]:
    """Validate and deserialize a JSON payload safely with size limits."""
    limit = max_bytes if max_bytes is not None else max_size_bytes
    if isinstance(raw_json, str):
        encoded = raw_json.encode("utf-8")
    elif isinstance(raw_json, bytes):
        encoded = raw_json
    else:
        raise ValueError(f"JSON input must be str or bytes, got {type(raw_json).__name__}")

    if len(encoded) > limit:
        raise ValueError(
            f"JSON payload size ({len(encoded)} bytes) exceeds maximum limit of {limit} bytes"
        )

    try:
        data = json.loads(encoded.decode("utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"Malformed JSON payload: {exc}") from exc

    if required_keys:
        if not isinstance(data, dict):
            raise ValueError(f"JSON payload must be an object (dict) to validate required keys: {required_keys}")
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"JSON payload is missing required keys: {missing}")

    return data


def validate_file_extension(
    filename_or_path: Union[str, Path],
    allowed_extensions: Optional[Set[str]] = None,
) -> str:
    """Validate a filename or path against allowed extension allowlist and check for double extensions."""
    p = Path(filename_or_path)
    name = p.name.lower()

    if "\x00" in name:
        raise ValueError("Filename contains forbidden null bytes (\\x00)")

    allowed = allowed_extensions or ALLOWED_DOCUMENT_EXTENSIONS

    # Check for dangerous double extensions (e.g. file.pdf.exe)
    parts = name.split(".")
    if len(parts) > 2:
        for ext_part in parts[1:]:
            dotted = f".{ext_part}"
            if dotted in DISALLOWED_EXECUTABLE_EXTENSIONS:
                raise ValueError(
                    f"Double extension detected: disallowed executable extension '{dotted}' in filename '{name}'"
                )

    suffix = p.suffix.lower()
    if suffix in DISALLOWED_EXECUTABLE_EXTENSIONS:
        raise ValueError(
            f"Dangerous executable extension '{suffix}' is strictly forbidden: '{name}'"
        )
    if not suffix or suffix not in allowed:
        raise ValueError(
            f"File extension '{suffix}' is not permitted. Allowed extensions: {sorted(allowed)}"
        )

    return suffix


def validate_file_size(
    size_bytes: int,
    max_size_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_bytes: Optional[int] = None,
) -> int:
    """Validate file size against maximum limit."""
    limit = max_bytes if max_bytes is not None else max_size_bytes
    if size_bytes < 0:
        raise ValueError(f"File size cannot be negative ({size_bytes} bytes)")
    if size_bytes > limit:
        raise ValueError(
            f"File size ({size_bytes} bytes) exceeds maximum allowed limit of {limit} bytes"
        )
    return size_bytes


EXTENSION_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".json": "application/json",
    ".csv": "text/csv",
    ".md": "text/markdown",
}


def validate_mime_type(content: bytes, expected_mime: Optional[str] = None) -> str:
    """Verify content against basic MIME magic byte signatures."""
    if not content:
        raise ValueError("File content is empty")

    # Map extension to mime if provided as an extension
    if expected_mime and expected_mime.startswith("."):
        expected_mime = EXTENSION_TO_MIME.get(expected_mime.lower(), expected_mime)

    detected_mime = "application/octet-stream"

    # PDF signature: starts with %PDF-
    if content.startswith(b"%PDF-"):
        detected_mime = "application/pdf"
    elif content.startswith(b"{\n") or content.startswith(b"{\r") or content.startswith(b'{"') or content.startswith(b"["):
        try:
            json.loads(content.decode("utf-8"))
            detected_mime = "application/json"
        except Exception:
            detected_mime = "text/plain"
    else:
        # Check if valid UTF-8 text
        try:
            content.decode("utf-8")
            detected_mime = "text/plain"
        except UnicodeDecodeError:
            detected_mime = "application/octet-stream"

    if expected_mime:
        # If expected is text/csv or text/markdown, text/plain is valid
        is_text_match = expected_mime in ("text/csv", "text/markdown", "text/plain") and detected_mime == "text/plain"
        if detected_mime != expected_mime and not is_text_match:
            if expected_mime == "application/pdf":
                raise ValueError("File does not match expected PDF signature (%PDF-)")
            raise ValueError(
                f"MIME verification failed: expected '{expected_mime}', but detected '{detected_mime}'"
            )

    return detected_mime


def validate_uploaded_file(
    filename: str,
    content_or_stream: Any,
    max_bytes: int = DEFAULT_MAX_FILE_BYTES,
    allowed_extensions: Optional[Set[str]] = None,
) -> dict:
    """Validate uploaded file extension, size, and content MIME signature."""
    ext = validate_file_extension(filename, allowed_extensions=allowed_extensions)
    if isinstance(content_or_stream, bytes):
        content = content_or_stream
    elif hasattr(content_or_stream, "read"):
        content = content_or_stream.read()
    else:
        raise ValueError(f"Content must be bytes or stream-like, got {type(content_or_stream).__name__}")

    validate_file_size(len(content), max_size_bytes=max_bytes)

    expected_mime = EXTENSION_TO_MIME.get(ext)
    detected_mime = validate_mime_type(content, expected_mime=expected_mime)

    return {
        "filename": Path(filename).name,
        "extension": ext,
        "size_bytes": len(content),
        "mime_type": detected_mime,
        "content": content,
    }

