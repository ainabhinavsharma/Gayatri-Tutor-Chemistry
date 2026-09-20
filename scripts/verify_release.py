#!/usr/bin/env python3
"""Gayatri AI - Release Integrity and Cryptographic Signature Verifier.

Verifies:
1. The Ed25519 signature of RELEASE_MANIFEST.json against RELEASE_MANIFEST.sig.
2. The SHA-256 cryptographic hashes of every packaged file in the release.
3. Absence of unauthorized injected files or missing components.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path for standalone script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.security.signatures import ManifestVerifier, OFFICIAL_TRUST_ANCHORS


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_release(
    release_dir: str | Path,
    public_key_b64: str | None = None,
    require_signature: bool = True,
) -> dict:
    """Verify release directory integrity and cryptographic signature.

    Returns:
        Dict with keys: valid (bool), signature_valid (bool), files_checked (int), errors (list[str])
    """
    rdir = Path(release_dir)
    if not rdir.is_dir():
        return {"valid": False, "error": f"Directory not found: {rdir}"}

    manifest_path = rdir / "RELEASE_MANIFEST.json"
    sig_path = rdir / "RELEASE_MANIFEST.sig"

    if not manifest_path.is_file():
        return {"valid": False, "error": "Missing RELEASE_MANIFEST.json"}

    errors: list[str] = []
    signature_valid = False

    # 1. Cryptographic Signature Verification
    if sig_path.is_file():
        keys_to_test = [public_key_b64] if public_key_b64 else OFFICIAL_TRUST_ANCHORS
        for key in keys_to_test:
            if key and ManifestVerifier.verify_file(manifest_path, sig_path, key):
                signature_valid = True
                break
        if not signature_valid:
            errors.append("Invalid or untrusted cryptographic signature on RELEASE_MANIFEST.json")
    elif require_signature:
        errors.append("Missing required RELEASE_MANIFEST.sig signature file")

    # 2. File Checksums Verification
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        files_dict: dict[str, str] = manifest_data.get("files", {})
    except Exception as exc:
        return {"valid": False, "error": f"Failed to parse manifest: {exc}"}

    files_checked = 0
    for rel_path, expected_hash in files_dict.items():
        actual_path = rdir / rel_path
        if not actual_path.is_file():
            errors.append(f"Missing release file: {rel_path}")
            continue

        actual_hash = compute_file_sha256(actual_path)
        if actual_hash != expected_hash:
            errors.append(f"Hash mismatch for {rel_path} (expected {expected_hash}, got {actual_hash})")
        else:
            files_checked += 1

    # 3. Check for unauthorized extra files
    ignored_names = {"RELEASE_MANIFEST.json", "RELEASE_MANIFEST.sig"}
    for p in rdir.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(rdir)).replace("\\", "/")
            if p.name not in ignored_names and rel not in files_dict:
                errors.append(f"Untracked or tampered file detected in release package: {rel}")

    return {
        "valid": len(errors) == 0,
        "signature_valid": signature_valid,
        "files_checked": files_checked,
        "errors": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Gayatri AI release distribution")
    parser.add_argument("release_dir", help="Path to release folder")
    parser.add_argument("--key", default=None, help="Base64 public key (optional)")
    parser.add_argument("--no-sig", action="store_true", help="Skip signature requirement")
    args = parser.parse_args()

    result = verify_release(args.release_dir, public_key_b64=args.key, require_signature=not args.no_sig)
    if result["valid"]:
        print(f"RELEASE INTEGRITY VERIFIED: {result['files_checked']} files verified successfully.")
        if result.get("signature_valid"):
            print("Cryptographic signature: VALID")
        sys.exit(0)
    else:
        print("RELEASE VERIFICATION FAILED:")
        for err in result.get("errors", [result.get("error")]):
            print(f"  - {err}")
        sys.exit(1)
