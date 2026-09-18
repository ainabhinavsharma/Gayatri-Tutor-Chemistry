"""Tests for Batch C: Model Downloader Preflight & Partial Cleanup.

Verifies fixes for Audit issues:
- #40: Model Download Resume Can Corrupt a Partial File If Server Ignores Range
- #41: Model Download Cancellation Leaves a Partial File That Looks Like a Valid Installation Candidate
- #44: Model Download Digest Is Not Persisted as Installation Metadata
- #59: File Downloads Need Disk-Space Preflight
"""

import hashlib
import json
from unittest.mock import MagicMock, patch
import pytest

from core.model_fetch.ollama_pull import (
    OllamaPullError,
    _download_blob,
    check_disk_space,
    cleanup_partial_downloads,
    get_model_metadata,
    pull_model,
    save_model_metadata,
)
from core.providers.local import LocalProvider
from app.bridge import Bridge


class TestDiskSpacePreflight:
    """Audit #59: Disk-space preflight before starting model blob downloads."""

    def test_check_disk_space_insufficient(self, tmp_path, monkeypatch):
        mock_usage = MagicMock()
        mock_usage.free = 150 * 1024 * 1024
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_usage)

        with pytest.raises(OllamaPullError) as exc_info:
            check_disk_space(tmp_path, required_bytes=100 * 1024 * 1024, safety_margin_bytes=100 * 1024 * 1024)

        assert "Insufficient disk space" in str(exc_info.value)
        assert "requires 100.0 MB" in str(exc_info.value)
        assert "150.0 MB is available" in str(exc_info.value)

    def test_check_disk_space_sufficient(self, tmp_path, monkeypatch):
        mock_usage = MagicMock()
        mock_usage.free = 500 * 1024 * 1024
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_usage)

        check_disk_space(tmp_path, required_bytes=100 * 1024 * 1024, safety_margin_bytes=100 * 1024 * 1024)

    def test_pull_model_aborts_on_insufficient_disk_space(self, tmp_path, monkeypatch):
        mock_manifest = MagicMock()
        mock_manifest.layers = [{"size": 500 * 1024 * 1024, "mediaType": "application/vnd.ollama.image.model"}]
        mock_manifest.model_blob = {"digest": "sha256:123456"}
        monkeypatch.setattr("core.model_fetch.ollama_pull._get_manifest", lambda ns, n, t: mock_manifest)

        mock_usage = MagicMock()
        mock_usage.free = 200 * 1024 * 1024
        monkeypatch.setattr("shutil.disk_usage", lambda path: mock_usage)

        with pytest.raises(OllamaPullError) as exc_info:
            pull_model(dest_dir=tmp_path)

        assert "Insufficient disk space" in str(exc_info.value)


class TestResumableRangeIntegrity:
    """Audit #40: Content-Range validation on HTTP 206 responses to prevent file corruption."""

    def test_download_blob_resume_with_matching_content_range(self, tmp_path):
        target_file = tmp_path / "model.bin"
        part_file = tmp_path / "model.bin.part"

        initial_content = b"Part1_"
        part_file.write_bytes(initial_content)

        remaining_content = b"Part2_End"
        full_content = initial_content + remaining_content
        expected_digest = hashlib.sha256(full_content).hexdigest()

        mock_resp = MagicMock()
        mock_resp.status_code = 206
        mock_resp.headers = {
            "content-range": f"bytes {len(initial_content)}-{len(full_content)-1}/{len(full_content)}"
        }
        mock_resp.iter_bytes.return_value = [remaining_content]
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("httpx.stream", return_value=mock_resp):
            _download_blob(
                url="https://registry.ollama.ai/v2/blob/test",
                dest=target_file,
                expected_digest=expected_digest,
            )

        assert target_file.exists()
        assert not part_file.exists()
        assert target_file.read_bytes() == full_content

    def test_download_blob_resume_with_mismatched_content_range_resets_file(self, tmp_path):
        target_file = tmp_path / "model.bin"
        part_file = tmp_path / "model.bin.part"

        part_file.write_bytes(b"0123456789")

        full_content = b"Fresh_Full_Content_From_Server"
        expected_digest = hashlib.sha256(full_content).hexdigest()

        mock_resp = MagicMock()
        mock_resp.status_code = 206
        mock_resp.headers = {
            "content-range": f"bytes 0-{len(full_content)-1}/{len(full_content)}"
        }
        mock_resp.iter_bytes.return_value = [full_content]
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("httpx.stream", return_value=mock_resp):
            _download_blob(
                url="https://registry.ollama.ai/v2/blob/test",
                dest=target_file,
                expected_digest=expected_digest,
            )

        assert target_file.exists()
        assert target_file.read_bytes() == full_content


class TestPartialFileIsolationAndCleanup:
    """Audit #41: Downloads use .part files so incomplete downloads cannot masquerade as installed."""

    def test_interrupted_download_leaves_only_part_file(self, tmp_path):
        target_file = tmp_path / "model.bin"
        part_file = tmp_path / "model.bin.part"

        chunk_data = b"first_chunk_of_data"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": "1000"}

        def iter_with_interrupt(chunk_size):
            yield chunk_data
            raise KeyboardInterrupt("Simulated user cancellation")

        mock_resp.iter_bytes = iter_with_interrupt
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("httpx.stream", return_value=mock_resp):
            with pytest.raises(KeyboardInterrupt):
                _download_blob(
                    url="https://registry.ollama.ai/v2/blob/test",
                    dest=target_file,
                    expected_digest="sha256:fake",
                )

        assert not target_file.exists()
        assert part_file.exists()
        assert part_file.read_bytes() == chunk_data

    def test_digest_mismatch_removes_part_and_does_not_create_dest(self, tmp_path):
        target_file = tmp_path / "model.bin"
        part_file = tmp_path / "model.bin.part"

        content = b"Some downloaded data"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-length": str(len(content))}
        mock_resp.iter_bytes.return_value = [content]
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("httpx.stream", return_value=mock_resp):
            with pytest.raises(OllamaPullError) as exc_info:
                _download_blob(
                    url="https://registry.ollama.ai/v2/blob/test",
                    dest=target_file,
                    expected_digest="sha256:wrong_digest_12345",
                )

        assert "Digest verification failed" in str(exc_info.value)
        assert not target_file.exists()
        assert not part_file.exists()

    def test_local_provider_health_detects_incomplete_download(self, tmp_path, monkeypatch):
        model_path = tmp_path / "model.gguf"
        part_path = tmp_path / "model.gguf.part"

        part_path.write_bytes(b"x" * (10 * 1024 * 1024))

        monkeypatch.setattr(LocalProvider, "MODEL_PATH", model_path)

        health = LocalProvider.health()
        assert health["available"] is False
        assert health["reason_code"] == "download_incomplete"
        assert "incomplete" in health["message"]

    def test_bridge_install_model_reports_not_installed_for_partial(self, tmp_path, monkeypatch):
        model_path = tmp_path / "model.gguf"
        part_path = tmp_path / "model.gguf.part"
        part_path.write_bytes(b"x" * (5 * 1024 * 1024))

        monkeypatch.setattr(LocalProvider, "MODEL_PATH", model_path)
        monkeypatch.setattr("core.config.MODELS_DIR", tmp_path)
        monkeypatch.setattr("core.config.LOCAL_MODEL_FILE", "model.gguf")

        monkeypatch.setattr(
            "core.model_fetch.ollama_pull.check_model_available",
            lambda: {"available": True, "size_mb": 500.0}
        )

        bridge = Bridge()
        status_raw = bridge.install_model()
        status = json.loads(status_raw)

        assert status["status"] == "not_installed"
        assert status["reason_code"] == "download_incomplete"

    def test_cleanup_partial_downloads(self, tmp_path):
        p1 = tmp_path / "model.gguf.part"
        p2 = tmp_path / "template.txt.part"
        f1 = tmp_path / "model.gguf"

        p1.write_bytes(b"partial1")
        p2.write_bytes(b"partial2")
        f1.write_bytes(b"finished")

        cleaned = cleanup_partial_downloads(tmp_path)
        assert "model.gguf.part" in cleaned
        assert "template.txt.part" in cleaned
        assert not p1.exists()
        assert not p2.exists()
        assert f1.exists()


class TestInstallationMetadataPersistence:
    """Audit #44: Model download digest and metadata persistence alongside installed model."""

    def test_save_and_retrieve_model_metadata(self, tmp_path):
        meta_path = save_model_metadata(
            dest_dir=tmp_path,
            model_file="model.gguf",
            digest="sha256:abcdef1234567890",
            namespace="DBERT",
            name="DBERT_AI",
            tag="latest",
            size_bytes=550000000,
            has_chat_template=True,
            has_params=True,
        )
        assert meta_path.exists()
        assert meta_path.name == "model.gguf.meta.json"

        loaded = get_model_metadata(dest_dir=tmp_path, model_file="model.gguf")
        assert loaded is not None
        assert loaded["digest"] == "sha256:abcdef1234567890"
        assert loaded["namespace"] == "DBERT"
        assert loaded["name"] == "DBERT_AI"
        assert loaded["tag"] == "latest"
        assert loaded["size_bytes"] == 550000000
        assert loaded["has_chat_template"] is True
        assert loaded["has_params"] is True
        assert "verified_at" in loaded

    def test_local_health_detects_corrupt_size_mismatch_against_metadata(self, tmp_path, monkeypatch):
        model_path = tmp_path / "model.gguf"
        model_path.write_bytes(b"x" * (2 * 1024 * 1024))

        save_model_metadata(
            dest_dir=tmp_path,
            model_file="model.gguf",
            digest="sha256:test",
            namespace="DBERT",
            name="DBERT_AI",
            tag="latest",
            size_bytes=500 * 1024 * 1024,
        )

        monkeypatch.setattr(LocalProvider, "MODEL_PATH", model_path)

        health = LocalProvider.health()
        assert health["available"] is False
        assert health["reason_code"] == "corrupt_file"
        assert "does not match verified installation metadata" in health["message"]

    def test_install_hook_model_exists_checks_structural_health(self, tmp_path, monkeypatch):
        from app.install_hook import InstallHook

        model_path = tmp_path / "model.gguf"
        monkeypatch.setattr(LocalProvider, "MODEL_PATH", model_path)
        monkeypatch.setattr(InstallHook, "EXPECTED_MODEL", model_path)

        hook = InstallHook()
        # 1. Model does not exist
        assert hook.model_exists() is False

        # 2. Only .part file exists
        part_path = tmp_path / "model.gguf.part"
        part_path.write_bytes(b"x" * (2 * 1024 * 1024))
        assert hook.model_exists() is False
        part_path.unlink()

        # 3. Model exists and healthy (mock llama_cpp)
        model_path.write_bytes(b"x" * (2 * 1024 * 1024))
        import sys
        import types
        fake_llama = types.ModuleType("llama_cpp")
        monkeypatch.setitem(sys.modules, "llama_cpp", fake_llama)
        assert hook.model_exists() is True

        # 4. Model size mismatch with metadata
        save_model_metadata(
            dest_dir=tmp_path,
            model_file="model.gguf",
            digest="sha256:test",
            namespace="DBERT",
            name="DBERT_AI",
            tag="latest",
            size_bytes=500 * 1024 * 1024,
        )
        assert hook.model_exists() is False
