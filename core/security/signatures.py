"""Cryptographic Signing and Verification Engine.

Provides asymmetric Ed25519 signature generation and verification for:
1. Release packages and distribution manifests (signed releases).
2. Model manifests and downloads (signed model manifests).
3. Canonical JSON serialization to prevent whitespace/key-ordering ambiguities.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger("gayatri.security.signatures")

# Built-in trust anchor public keys for official Gayatri distributions
OFFICIAL_TRUST_ANCHORS: list[str] = [
    # Official Release Signing Authority (Test & Staging Key)
    "MCowBQYDK2VwAyEA9ZkH8cZ4y5T6Z2a4b8c9d0e1f2a3b4c5d6e7f8a9b0c="
]


class CryptographicError(Exception):
    """Base exception for signature verification or key management errors."""


def canonicalize_json(data: dict[str, Any] | list[Any]) -> bytes:
    """Serialize dictionary/list into deterministic UTF-8 bytes without extraneous whitespace."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class ManifestSigner:
    """Signs files and structured manifests using Ed25519 private keys."""

    @staticmethod
    def generate_keypair() -> tuple[str, str]:
        """Generate a new Ed25519 keypair encoded as base64 strings.
        
        Returns:
            tuple of (private_key_b64, public_key_b64)
        """
        priv_key = ed25519.Ed25519PrivateKey.generate()
        pub_key = priv_key.public_key()

        priv_bytes = priv_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = pub_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        return (
            base64.b64encode(priv_bytes).decode("ascii"),
            base64.b64encode(pub_bytes).decode("ascii"),
        )

    @classmethod
    def sign_bytes(cls, data: bytes, private_key_b64: str) -> str:
        """Sign raw bytes with an Ed25519 private key.
        
        Returns:
            Base64-encoded signature string.
        """
        try:
            priv_bytes = base64.b64decode(private_key_b64.strip())
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
            sig_bytes = priv_key.sign(data)
            return base64.b64encode(sig_bytes).decode("ascii")
        except Exception as exc:
            raise CryptographicError(f"Failed to sign data: {exc}") from exc

    @classmethod
    def sign_file(cls, file_path: str | Path, private_key_b64: str, sig_output_path: str | Path | None = None) -> Path:
        """Sign a file on disk and write a detached base64 signature file."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Cannot sign non-existent file: {path}")

        sig_b64 = cls.sign_bytes(path.read_bytes(), private_key_b64)
        out_path = Path(sig_output_path) if sig_output_path else path.with_suffix(path.suffix + ".sig")
        out_path.write_text(sig_b64.strip() + "\n", encoding="utf-8")
        logger.info(f"Signed file {path.name} -> {out_path.name}")
        return out_path

    @classmethod
    def sign_manifest(cls, manifest: dict[str, Any], private_key_b64: str) -> dict[str, Any]:
        """Sign a manifest dictionary and return a self-contained signed envelope."""
        clean_manifest = {k: v for k, v in manifest.items() if k != "signature"}
        data = canonicalize_json(clean_manifest)
        sig = cls.sign_bytes(data, private_key_b64)
        
        signed_manifest = dict(clean_manifest)
        signed_manifest["signature"] = {
            "algorithm": "ed25519",
            "value": sig,
        }
        return signed_manifest


class ManifestVerifier:
    """Verifies detached and enveloped signatures using Ed25519 public keys."""

    @classmethod
    def verify_bytes(cls, data: bytes, signature_b64: str, public_key_b64: str) -> bool:
        """Verify an Ed25519 signature over raw bytes."""
        try:
            pub_bytes = base64.b64decode(public_key_b64.strip())
            sig_bytes = base64.b64decode(signature_b64.strip())
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            pub_key.verify(sig_bytes, data)
            return True
        except (InvalidSignature, ValueError, Exception) as exc:
            logger.debug(f"Signature verification failed: {exc}")
            return False

    @classmethod
    def verify_file(cls, file_path: str | Path, sig_path: str | Path, public_key_b64: str) -> bool:
        """Verify a detached signature file against a target file."""
        fp = Path(file_path)
        sp = Path(sig_path)
        if not fp.is_file():
            raise FileNotFoundError(f"Target file not found: {fp}")
        if not sp.is_file():
            raise FileNotFoundError(f"Signature file not found: {sp}")

        sig_b64 = sp.read_text(encoding="utf-8").strip()
        data = fp.read_bytes()
        return cls.verify_bytes(data, sig_b64, public_key_b64)

    @classmethod
    def verify_manifest(cls, signed_manifest: dict[str, Any], public_key_b64: str) -> bool:
        """Verify an enveloped signed manifest dictionary."""
        sig_meta = signed_manifest.get("signature")
        if not sig_meta or not isinstance(sig_meta, dict):
            logger.warning("Manifest missing signature object")
            return False

        sig_b64 = sig_meta.get("value")
        if not sig_b64:
            return False

        clean_manifest = {k: v for k, v in signed_manifest.items() if k != "signature"}
        data = canonicalize_json(clean_manifest)
        return cls.verify_bytes(data, sig_b64, public_key_b64)

    @classmethod
    def verify_against_trust_anchors(
        cls,
        data: bytes,
        signature_b64: str,
        trusted_keys: list[str] | None = None,
    ) -> tuple[bool, str | None]:
        """Verify signature against an allowlist of trusted public keys.
        
        Returns:
            tuple of (is_valid, matching_public_key or None)
        """
        keys = trusted_keys or OFFICIAL_TRUST_ANCHORS
        for pub_key in keys:
            if cls.verify_bytes(data, signature_b64, pub_key):
                return True, pub_key
        return False, None
