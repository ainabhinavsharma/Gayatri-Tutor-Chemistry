"""Tests for Phase 13: Silent Failures Re-Audit (P13-T01 to P13-T05)."""
import pytest
from core.errors import sanitize_message, sanitize_error, SanitizedError


def test_sanitize_message_redaction():
    """Test redaction of paths, URLs, tokens, and API keys from error strings."""
    raw = (
        "Error at C:\\Users\\Administrator\\secret\\config.json "
        "or /var/root/data.txt calling https://api.openai.com/v1/chat "
        "with key AIzaSyD1234567890123456789012345678901 and Bearer token123xyz"
    )
    clean = sanitize_message(raw)

    assert "C:\\Users\\" not in clean
    assert "/var/root/" not in clean
    assert "https://api.openai.com" not in clean
    assert "AIzaSyD" not in clean
    assert "[LOCAL_PATH]" in clean
    assert "[ENDPOINT_URL]" in clean
    assert "[GOOGLE_API_KEY]" in clean
    assert "[REDACTED_TOKEN]" in clean


def test_sanitize_error_diagnostic_id():
    """Test diagnostic ID generation and structure."""
    err = sanitize_error(ValueError("Invalid parameter value"))
    assert isinstance(err, SanitizedError)
    assert err.diagnostic_id.startswith("ERR-")
    assert len(err.diagnostic_id) == 12  # ERR- + 8 hex chars
    assert err.category == "validation"


def test_sanitize_error_categories():
    """Test exception category mapping."""
    # Model unavailable
    err_mod = sanitize_error(RuntimeError("Model unavailable error"))
    assert err_mod.category == "model_unavailable"
    assert "unavailable" in err_mod.user_message.lower()

    # Privacy mode / Local-Only
    err_priv = sanitize_error(PermissionError("Data cannot leave the device in privacy mode"))
    assert err_priv.category == "privacy_policy"
    assert "privacy policy" in err_priv.user_message.lower()

    # File not found
    err_fnf = sanitize_error(FileNotFoundError("No such file or directory model.gguf"))
    assert err_fnf.category == "file_not_found"

    # Timeout
    err_to = sanitize_error(TimeoutError("Request timeout"))
    assert err_to.category == "timeout"

    # Network connection error
    err_net = sanitize_error(ConnectionError("Connection refused by target host"))
    assert err_net.category == "network_connection"

    # Authentication failure
    err_auth = sanitize_error(RuntimeError("HTTP 401 Unauthorized: invalid api key"))
    assert err_auth.category == "authentication"
