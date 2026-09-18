import os
import json
from core.security.secrets import SecretsVault

def test_secrets_vault_fernet_fallback(tmp_path):
    # Ensure non-Windows platforms use the secure Fernet fallback
    vault = SecretsVault(tmp_path / "secrets.enc")
    vault._is_windows = False
    
    # It should successfully store and retrieve using Fernet
    vault.store_key("test_key", "test_val")
    assert vault.retrieve_key("test_key") == "test_val"

    # Verify it is not stored in plaintext
    with open(tmp_path / "secrets.enc", "rb") as f:
        data = json.loads(f.read().decode("utf-8"))
        assert "test_val" not in data["test_key"]

def test_secrets_vault_corrupt_entry(tmp_path):
    vault = SecretsVault(tmp_path / "secrets.enc")
    vault._is_windows = False
    
    # Store multiple keys
    vault.store_key("key1", "val1")
    vault.store_key("key2", "val2")
    
    # Corrupt key1 manually
    with open(vault.vault_path, "r") as f:
        data = json.load(f)
    data["key1"] = "invalid_base64_!@#"
    with open(vault.vault_path, "w") as f:
        json.dump(data, f)
        
    # Read vault, key1 should be skipped but not deleted
    assert vault.retrieve_key("key2") == "val2"
    assert vault.retrieve_key("key1") is None
    
    # Store a new key
    vault.store_key("key3", "val3")
    
    # Read the JSON file directly, key1 should still be there
    with open(vault.vault_path, "r") as f:
        data = json.load(f)
    assert "key1" in data
    assert data["key1"] == "invalid_base64_!@#"
    assert "key2" in data
    assert "key3" in data

    # Delete key1
    vault.delete_key("key1")
    with open(vault.vault_path, "r") as f:
        data = json.load(f)
    assert "key1" not in data

def test_secrets_vault_windows_dpapi(tmp_path):
    # Only test DPAPI if running on Windows
    if os.name == 'nt':
        vault = SecretsVault(tmp_path / "secrets_dpapi.enc")
        vault.store_key("dpapi_key", "dpapi_val")
        assert vault.retrieve_key("dpapi_key") == "dpapi_val"
        vault.delete_key("dpapi_key")
        assert vault.retrieve_key("dpapi_key") is None

