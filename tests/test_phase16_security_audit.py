"""Phase 16: Security Audit Verification Tests (Section 22).

Verifies:
1. Environment variable fallback for API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY).
2. Vault precedence over environment variables.
3. Governance PIN hashing (SHA-256) and timing-safe comparison (secrets.compare_digest).
4. Legacy plaintext PIN migration to hash.
5. Sensitive credentials sanitization in logs and error messages.
6. Git protection (.gitignore) for secrets, .env files, and cryptographic keys.
"""
import hashlib
from pathlib import Path
import pytest

from core.security.secrets import SecretsVault
from core.governance import GovernanceManager, _hash_pin
from core.errors import sanitize_error
from core.security.authorization import StudentAuthorizationGuard


def test_env_variable_fallback_for_api_keys(tmp_path, monkeypatch):
    """Verify Section 22: environment variables are resolved when keys are not in the vault."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-env-openai-12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-env-67890")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyTestEnvGoogleKey111")

    vault_file = tmp_path / "secrets.enc"
    vault = SecretsVault(vault_path=vault_file)

    assert vault.retrieve_key("openai") == "sk-test-env-openai-12345"
    assert vault.retrieve_key("anthropic") == "sk-ant-test-env-67890"
    assert vault.retrieve_key("google") == "AIzaSyTestEnvGoogleKey111"

    assert vault.has_key("openai") is True
    assert vault.has_key("anthropic") is True
    assert vault.has_key("google") is True
    assert vault.has_key("nonexistent_provider") is False


def test_vault_takes_precedence_over_env(tmp_path, monkeypatch):
    """Verify Section 22: explicitly configured vault secrets take precedence over environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key-should-be-overridden")

    vault_file = tmp_path / "secrets.enc"
    vault = SecretsVault(vault_path=vault_file)

    # Store explicitly in vault
    vault.store_key("openai", "sk-vault-key-authoritative")

    assert vault.retrieve_key("openai") == "sk-vault-key-authoritative"


def test_governance_pin_hashing_and_timing_safe_verification(tmp_path):
    """Verify Section 22: PINs are stored as SHA-256 hashes, not plaintext, and verified timing-safely."""
    db_path = tmp_path / "test_gov_secure.db"
    mgr = GovernanceManager(db_path=db_path)

    # Verify default PIN works
    assert mgr.verify_pin("1234") is True
    assert mgr.verify_pin("0000") is False

    # Check database content: MUST NOT be plaintext "1234"
    conn = mgr._get_conn()
    try:
        row = conn.execute("SELECT val FROM governance_settings WHERE key = 'admin_pin';").fetchone()
        stored_val = row["val"]
        assert stored_val != "1234"
        assert len(stored_val) == 64  # SHA-256 hex digest length
        assert stored_val == _hash_pin("1234")
    finally:
        conn.close()

    # Update PIN
    assert mgr.set_pin("1234", "9876") is True
    assert mgr.verify_pin("9876") is True
    assert mgr.verify_pin("1234") is False

    # Verify updated database content is the hash of 9876
    conn = mgr._get_conn()
    try:
        row = conn.execute("SELECT val FROM governance_settings WHERE key = 'admin_pin';").fetchone()
        assert row["val"] == _hash_pin("9876")
    finally:
        conn.close()


def test_governance_legacy_plaintext_migration(tmp_path):
    """Verify Section 22: legacy plaintext PIN is verified and automatically migrated to SHA-256 hash."""
    db_path = tmp_path / "test_gov_legacy.db"
    mgr = GovernanceManager(db_path=db_path)

    # Force a plaintext PIN into the database
    conn = mgr._get_conn()
    try:
        with conn:
            conn.execute("UPDATE governance_settings SET val = 'legacy_plaintext_5555' WHERE key = 'admin_pin';")
    finally:
        conn.close()

    # Verification should succeed and transparently migrate
    assert mgr.verify_pin("legacy_plaintext_5555") is True

    # Check database content: now migrated to hash
    conn = mgr._get_conn()
    try:
        row = conn.execute("SELECT val FROM governance_settings WHERE key = 'admin_pin';").fetchone()
        assert row["val"] == _hash_pin("legacy_plaintext_5555")
        assert row["val"] != "legacy_plaintext_5555"
    finally:
        conn.close()


def test_sensitive_keys_sanitization():
    """Verify Section 22: credentials, tokens, and keys are scrubbed from logs and errors."""
    log_text = "Failed request to https://api.example.com?key=AIzaSySecretGoogleKey123 with token=my_secret_token"
    cleaned = StudentAuthorizationGuard.sanitize_log_record(log_text)
    assert "AIzaSySecretGoogleKey123" not in cleaned
    assert "my_secret_token" not in cleaned

    err_text = "Connection error to provider with api_key=sk-1234567890abcdef12345678 and key=AIzaSy12345"
    from core.errors import sanitize_message
    sanitized_text = sanitize_message(err_text)
    assert "sk-1234567890abcdef12345678" not in sanitized_text

    err = RuntimeError("Connection error to provider with api_key=sk-1234567890abcdef12345678")
    sanitized = sanitize_error(err)
    assert "sk-1234567890abcdef12345678" not in sanitized.user_message


def test_gitignore_protects_credentials():
    """Verify Section 22: .gitignore contains critical secret and key patterns."""
    repo_root = Path(__file__).parent.parent
    gitignore_path = repo_root / ".gitignore"
    assert gitignore_path.exists()

    content = gitignore_path.read_text()
    assert ".env" in content
    assert "secrets.enc" in content
    assert "*.key" in content
    assert "*.pem" in content
