"""Gayatri AI — Logging setup with PII/credential redaction."""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from core.config import LOG_BACKUP_COUNT, LOG_DATE_FORMAT, LOG_DIR, LOG_FORMAT, LOG_MAX_BYTES

# Patterns that should NEVER appear in logs
_CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),           # OpenAI keys
    re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"),     # Anthropic keys (Audit #92)
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),        # Google API keys
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*\S+"),   # Generic API key assignments
    re.compile(r"(?i)password\s*[:=]\s*\S+"),      # Password assignments
    re.compile(r"(?i)secret\s*[:=]\s*\S+"),        # Secret assignments
    re.compile(r"(?i)token\s*[:=]\s*\S+"),         # Token assignments
    re.compile(r"-----BEGIN [A-Z ]+-----"),         # PEM blocks
]


def _redact(text: str) -> str:
    for pat in _CREDENTIAL_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(str(record.msg))
        if record.args:
            record.args = tuple(_redact(str(a)) for a in record.args)
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging: console + rotating file, with redaction filter."""
    logger = logging.getLogger("gayatri")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.addFilter(_RedactFilter())

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (rotating)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "gayatri.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
