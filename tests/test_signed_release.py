"""Tests for Phase 5: Signed Release Packaging and Verification."""

from pathlib import Path
from core.security.signatures import ManifestSigner
from scripts.package_release import package_release
from scripts.verify_release import verify_release


def test_signed_release_packaging_and_verification(tmp_path):
    priv, pub = ManifestSigner.generate_keypair()

    # Create dummy source repo
    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "core").mkdir()
    (src_root / "core" / "app.py").write_text("print('gayatri')", encoding="utf-8")
    (src_root / "VERSION").write_text("3.0.0\n", encoding="utf-8")
    (src_root / "README.md").write_text("# Gayatri AI", encoding="utf-8")

    out_dir = tmp_path / "dist" / "gayatri-v3.0.0"

    # Package with signing
    pack_res = package_release(
        source_root=src_root,
        output_dir=out_dir,
        version="3.0.0",
        signing_key_b64=priv,
    )

    assert pack_res["signature_path"] is not None
    assert Path(pack_res["manifest_path"]).is_file()
    assert Path(pack_res["signature_path"]).is_file()

    # Verify signed release
    verify_res = verify_release(out_dir, public_key_b64=pub, require_signature=True)
    assert verify_res["valid"] is True
    assert verify_res["signature_valid"] is True
    assert verify_res["files_checked"] >= 2


def test_verify_release_detects_tampered_file(tmp_path):
    priv, pub = ManifestSigner.generate_keypair()

    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "core").mkdir()
    (src_root / "core" / "module.py").write_text("def run(): pass", encoding="utf-8")

    out_dir = tmp_path / "dist" / "release_tamper"
    package_release(source_root=src_root, output_dir=out_dir, signing_key_b64=priv)

    # Tamper with file
    (out_dir / "core" / "module.py").write_text("def run(): exploit()", encoding="utf-8")

    res = verify_release(out_dir, public_key_b64=pub)
    assert res["valid"] is False
    assert any("Hash mismatch" in err for err in res["errors"])


def test_verify_release_detects_injected_file(tmp_path):
    priv, pub = ManifestSigner.generate_keypair()

    src_root = tmp_path / "src"
    src_root.mkdir()
    (src_root / "core").mkdir()
    (src_root / "core" / "safe.py").write_text("x = 1", encoding="utf-8")

    out_dir = tmp_path / "dist" / "release_inject"
    package_release(source_root=src_root, output_dir=out_dir, signing_key_b64=priv)

    # Inject unauthorized file
    (out_dir / "core" / "backdoor.py").write_text("import os; os.system()", encoding="utf-8")

    res = verify_release(out_dir, public_key_b64=pub)
    assert res["valid"] is False
    assert any("Untracked or tampered file detected" in err for err in res["errors"])
