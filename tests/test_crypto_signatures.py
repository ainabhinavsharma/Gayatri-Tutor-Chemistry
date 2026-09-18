"""Tests for Phase 5: Cryptographic Signing and Integrity Engine."""

import pytest
from pathlib import Path
from core.security.signatures import (
    ManifestSigner,
    ManifestVerifier,
)
from core.model_fetch.ollama_pull import ModelManifest, pull_model, OllamaPullError


def test_ed25519_keypair_generation():
    priv, pub = ManifestSigner.generate_keypair()
    assert isinstance(priv, str) and len(priv) > 20
    assert isinstance(pub, str) and len(pub) > 20
    assert priv != pub


def test_sign_and_verify_bytes():
    priv, pub = ManifestSigner.generate_keypair()
    data = b"Gayatri Tutor V3 Educational Integrity"

    sig = ManifestSigner.sign_bytes(data, priv)
    assert ManifestVerifier.verify_bytes(data, sig, pub) is True

    # Tampered data must fail
    assert ManifestVerifier.verify_bytes(data + b"!", sig, pub) is False

    # Wrong key must fail
    _, other_pub = ManifestSigner.generate_keypair()
    assert ManifestVerifier.verify_bytes(data, sig, other_pub) is False


def test_sign_and_verify_file(tmp_path):
    priv, pub = ManifestSigner.generate_keypair()
    target_file = tmp_path / "payload.bin"
    target_file.write_bytes(b"Sensitive application binary data")

    sig_file = ManifestSigner.sign_file(target_file, priv)
    assert sig_file.is_file()
    assert ManifestVerifier.verify_file(target_file, sig_file, pub) is True

    # Tamper file
    target_file.write_bytes(b"Tampered application binary data")
    assert ManifestVerifier.verify_file(target_file, sig_file, pub) is False


def test_sign_and_verify_enveloped_manifest():
    priv, pub = ManifestSigner.generate_keypair()
    manifest = {
        "version": "3.0.0",
        "models": ["gemma-2-2b", "gemma-2-9b"],
        "curriculum": "CBSE-Grade-9",
    }

    signed = ManifestSigner.sign_manifest(manifest, priv)
    assert "signature" in signed
    assert signed["signature"]["algorithm"] == "ed25519"
    assert ManifestVerifier.verify_manifest(signed, pub) is True

    # Tampering with payload fails
    tampered = dict(signed)
    tampered["version"] = "3.0.1"
    assert ManifestVerifier.verify_manifest(tampered, pub) is False


def test_model_manifest_signature_verification():
    priv, pub = ManifestSigner.generate_keypair()
    manifest_data = {
        "config": {"digest": "sha256:11223344"},
        "layers": [{"mediaType": "application/vnd.ollama.image.model", "digest": "sha256:55667788", "size": 1024}],
    }

    signed_data = ManifestSigner.sign_manifest(manifest_data, priv)
    mm = ModelManifest.from_dict(signed_data)
    assert mm.verify_signature(pub) is True

    # Unsigned manifest
    unsigned_mm = ModelManifest.from_dict(manifest_data)
    assert unsigned_mm.verify_signature(pub) is False


def test_pull_model_signature_enforcement(monkeypatch, tmp_path):
    priv, pub = ManifestSigner.generate_keypair()
    dummy_manifest = {
        "config": {"digest": "sha256:mockdigest"},
        "layers": [{"mediaType": "application/vnd.ollama.image.model", "digest": "sha256:mockmodel", "size": 512}],
    }

    signed_manifest = ManifestSigner.sign_manifest(dummy_manifest, priv)

    # Mock _get_manifest to return our manifest
    monkeypatch.setattr(
        "core.model_fetch.ollama_pull._get_manifest",
        lambda ns, n, t: ModelManifest.from_dict(signed_manifest),
    )
    monkeypatch.setattr("core.model_fetch.ollama_pull.check_disk_space", lambda p, s: None)
    monkeypatch.setattr("core.model_fetch.ollama_pull._download_blob", lambda u, p, d, *a, **kw: Path(p).write_bytes(b"data"))

    # Successful pull with valid trusted key
    res = pull_model(
        dest_dir=tmp_path,
        require_signed_manifest=True,
        trusted_public_keys=[pub],
    )
    assert res["digest"] == "sha256:mockmodel"

    # Failed pull with untrusted key
    _, wrong_pub = ManifestSigner.generate_keypair()
    with pytest.raises(OllamaPullError, match="cryptographic signature verification failed"):
        pull_model(
            dest_dir=tmp_path,
            require_signed_manifest=True,
            trusted_public_keys=[wrong_pub],
        )
