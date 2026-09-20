#!/usr/bin/env python3
"""Gayatri AI - Automated Release Packager & Integrity Manifest Generator.

Packages application assets into a distributable release directory,
computes cryptographic SHA-256 checksums, and optionally cryptographically
signs the release manifest with an Ed25519 private key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def package_release(
    source_root: Path | None = None,
    output_dir: Path | None = None,
    version: str = "3.0.0",
    signing_key_b64: str | None = None,
) -> dict:
    """Package release files and produce a signed integrity manifest."""
    root = source_root or Path(__file__).resolve().parent.parent
    out = output_dir or (root / "dist" / f"gayatri-ai-v{version}")

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    # Directories and files to include in distribution
    include_dirs = ["app", "core", "data", "docs", "legacy"]
    include_files = [
        "launch.bat",
        "setup.bat",
        "requirements.txt",
        "requirements.lock",
        "pyproject.toml",
        "README.md",
        "VERSION",
        "CHANGELOG.md",
        "RELEASE_NOTES.md",
    ]

    for d in include_dirs:
        src_dir = root / d
        if src_dir.exists():
            shutil.copytree(
                src_dir,
                out / d,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"),
            )

    for f in include_files:
        src_file = root / f
        if src_file.exists():
            shutil.copy2(src_file, out / f)

    # Compute SHA-256 manifest
    file_manifest: dict[str, str] = {}
    for p in out.rglob("*"):
        if p.is_file() and p.name not in ("RELEASE_MANIFEST.json", "RELEASE_MANIFEST.sig"):
            rel_path = str(p.relative_to(out)).replace("\\", "/")
            file_manifest[rel_path] = compute_file_sha256(p)

    manifest_data = {
        "project": "Gayatri AI",
        "version": version,
        "platform": "windows-x64",
        "target_python": ">=3.12, <3.13",
        "packaged_at": datetime.now().isoformat(),
        "total_files": len(file_manifest),
        "files": file_manifest,
    }

    manifest_path = out / "RELEASE_MANIFEST.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest_data, mf, indent=2)

    sig_path = None
    if signing_key_b64:
        from core.security.signatures import ManifestSigner
        sig_path = ManifestSigner.sign_file(manifest_path, signing_key_b64, out / "RELEASE_MANIFEST.sig")

    return {
        "output_directory": str(out),
        "version": version,
        "total_files": len(file_manifest),
        "manifest_path": str(manifest_path),
        "signature_path": str(sig_path) if sig_path else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Gayatri AI release")
    parser.add_argument("--version", default="3.0.0", help="Release version string")
    parser.add_argument("--sign-key", default=None, help="Base64-encoded Ed25519 private key for signing")
    args = parser.parse_args()

    res = package_release(version=args.version, signing_key_b64=args.sign_key)
    print(f"Packaged Gayatri AI release: {res['total_files']} files to {res['output_directory']}")
    if res.get("signature_path"):
        print(f"Signed release manifest: {res['signature_path']}")
