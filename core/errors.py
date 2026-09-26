"""Gayatri AI — Error sanitization and diagnostic tracking.

Ensures internal paths, stack traces, provider URLs, and API keys
never leak into user-facing UI messages or chat histories.
Provides structured diagnostic IDs for correlation with local logs.
"""

from __future__ import annotations

import logging
import re
import traceback
import uuid
from dataclasses import dataclass

logger = logging.getLogger("gayatri.errors")

# Regex patterns for stripping sensitive technical data from error strings
_RE_WIN_PATH = re.compile(r"[A-Za-z]:[\\/][^ \r\n\"'>:]+")
_RE_POSIX_PATH = re.compile(r"/(?:Users|home|root|var|etc|usr|opt|tmp|app|core)/[^ \r\n\"'>:]+")
_RE_URL = re.compile(r"https?://[^\s\"'>]+")
_RE_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE)
_RE_API_KEY_QUERY = re.compile(r"[?&]key=[^&\s\"'>]+", re.IGNORECASE)
_RE_API_KEY_GOOGLE = re.compile(r"AIza[0-9A-Za-z\-_]{30,40}")
_RE_API_KEY_ANTHROPIC = re.compile(r"sk-ant-[0-9A-Za-z\-_]{20,}")
_RE_API_KEY_OPENAI = re.compile(r"sk-[0-9A-Za-z\-_]{20,}")
_RE_TRACEBACK_LINE = re.compile(r'File ".*?", line \d+, in .*')


def sanitize_message(raw_text: str) -> str:
    """Strip filesystem paths, API keys, URLs, and traceback indicators from arbitrary text."""
    if not raw_text:
        return ""

    sanitized = raw_text
    sanitized = _RE_API_KEY_QUERY.sub("[API_KEY_PARAM]", sanitized)
    sanitized = _RE_API_KEY_GOOGLE.sub("[GOOGLE_API_KEY]", sanitized)
    sanitized = _RE_API_KEY_ANTHROPIC.sub("[ANTHROPIC_API_KEY]", sanitized)
    sanitized = _RE_API_KEY_OPENAI.sub("[OPENAI_API_KEY]", sanitized)
    sanitized = _RE_BEARER.sub("Bearer [REDACTED_TOKEN]", sanitized)
    sanitized = _RE_URL.sub("[ENDPOINT_URL]", sanitized)
    sanitized = _RE_WIN_PATH.sub("[LOCAL_PATH]", sanitized)
    sanitized = _RE_POSIX_PATH.sub("[LOCAL_PATH]", sanitized)
    sanitized = _RE_TRACEBACK_LINE.sub("[TRACEBACK_FRAME]", sanitized)
    return sanitized


@dataclass
class SanitizedError:
    """Structured, safe error representation separating UI display from local diagnostics."""
    user_message: str
    diagnostic_id: str
    internal_error: str
    category: str = "general"

    def __str__(self) -> str:
        return self.user_message


def sanitize_error(exc: Exception | str, category: str = "general") -> SanitizedError:
    """Create a SanitizedError from an exception or raw error message.

    1. Generates a unique diagnostic ID (e.g., ERR-1A2B3C4D).
    2. Logs the full technical traceback locally with the diagnostic ID.
    3. Returns a user-facing message free of file paths, keys, or stack traces.
    """
    diagnostic_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"

    if isinstance(exc, Exception):
        tb_str = traceback.format_exc()
        if tb_str and tb_str.strip() != "NoneType: None":
            internal_error = tb_str
        else:
            internal_error = f"{type(exc).__name__}: {exc}"
        exc_name = type(exc).__name__
        exc_str = str(exc)
    else:
        internal_error = str(exc)
        exc_name = "Error"
        exc_str = str(exc)

    # Log full technical details with diagnostic ID locally
    logger.error(f"[{diagnostic_id}] Internal failure ({category}): {internal_error}")

    # Determine user-friendly safe message
    lower_str = exc_str.lower()

    if exc_name == "ModelUnavailableError" or "model unavailable" in lower_str or "model_unavailable" in lower_str:
        user_msg = "The requested AI model is currently unavailable. Please check your model installation in Settings."
        detected_category = "model_unavailable"
    elif exc_name == "PermissionError" or "privacy mode" in lower_str or "data cannot leave the device" in lower_str:
        user_msg = "Operation blocked by privacy policy: Cloud providers are disabled in Local-Only mode."
        detected_category = "privacy_policy"
    elif exc_name == "FileNotFoundError" or "no such file" in lower_str or ".gguf" in lower_str:
        user_msg = "A required local model or data file could not be found. Please check your model settings."
        detected_category = "file_not_found"
    elif "timeout" in lower_str or exc_name == "TimeoutError":
        user_msg = "The request timed out while communicating with the model provider. Please try again."
        detected_category = "timeout"
    elif any(term in lower_str for term in ("failed to establish a new connection", "connection refused", "nodename nor servname", "network is unreachable", "connecterror")):
        user_msg = "Unable to connect to the network or provider endpoint. Please check your connection."
        detected_category = "network_connection"
    elif any(term in lower_str for term in ("401", "unauthorized", "invalid api key", "authentication")):
        user_msg = "Authentication failed for the selected provider. Please verify your API key in Settings."
        detected_category = "authentication"
    elif any(term in lower_str for term in ("429", "rate limit", "quota exceeded")):
        user_msg = "Provider rate limit or quota exceeded. Please wait a moment and try again."
        detected_category = "rate_limit"
    elif exc_name in ("ValueError", "KeyError", "TypeError"):
        # Strip paths / keys even from value errors
        clean = sanitize_message(exc_str)
        user_msg = f"Invalid input or configuration: {clean}"
        detected_category = "validation"
    else:
        # Sanitize any paths, URLs, and keys from the message
        clean_text = sanitize_message(exc_str)
        if len(clean_text) > 200 or "traceback" in clean_text.lower() or "syntaxerror" in clean_text.lower():
            user_msg = f"An unexpected error occurred (Reference: {diagnostic_id}). Please check the application logs for details."
        else:
            user_msg = clean_text
        detected_category = category or "general"

    return SanitizedError(
        user_message=user_msg,
        diagnostic_id=diagnostic_id,
        internal_error=internal_error,
        category=detected_category,
    )
