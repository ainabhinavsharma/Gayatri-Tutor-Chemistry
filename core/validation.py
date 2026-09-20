"""Gayatri AI — Validation Re-exports.

Authoritative re-exports of zero-trust input validators.
"""
from core.security.validation import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    DISALLOWED_EXECUTABLE_EXTENSIONS,
    DEFAULT_MAX_QUERY_LENGTH,
    DEFAULT_MAX_PROMPT_LENGTH,
    DEFAULT_MAX_JSON_BYTES,
    DEFAULT_MAX_FILE_BYTES,
    validate_student_id,
    validate_session_id,
    validate_concept_id,
    validate_question_id,
    validate_query_text,
    validate_prompt_text,
    validate_json,
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
    validate_uploaded_file,
    EXTENSION_TO_MIME,
)

__all__ = [
    "ALLOWED_DOCUMENT_EXTENSIONS",
    "DISALLOWED_EXECUTABLE_EXTENSIONS",
    "DEFAULT_MAX_QUERY_LENGTH",
    "DEFAULT_MAX_PROMPT_LENGTH",
    "DEFAULT_MAX_JSON_BYTES",
    "DEFAULT_MAX_FILE_BYTES",
    "validate_student_id",
    "validate_session_id",
    "validate_concept_id",
    "validate_question_id",
    "validate_query_text",
    "validate_prompt_text",
    "validate_json",
    "validate_file_extension",
    "validate_file_size",
    "validate_mime_type",
    "validate_uploaded_file",
    "EXTENSION_TO_MIME",
]
