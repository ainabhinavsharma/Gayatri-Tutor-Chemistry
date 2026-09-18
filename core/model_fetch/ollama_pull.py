"""Gayatri AI — Ollama registry model puller.

Downloads GGUF models from registry.ollama.ai WITHOUT needing Ollama installed.
Handles manifest parsing, resumable blob downloads, and sha256 verification.

Confirmed model: DBERT/DBERT_AI:latest (531 MB, 32K ctx, GGUF)
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger("gayatri.model_fetch")

# Ollama registry base URL
OLLAMA_REGISTRY = "https://registry.ollama.ai"

# Confirmed model coordinates
DEFAULT_MODEL_NAMESPACE = "DBERT"
DEFAULT_MODEL_NAME = "DBERT_AI"
DEFAULT_MODEL_TAG = "latest"

# Approved Model Allowlist (Audit #MODEL-002)
APPROVED_MODELS = {
    ("dbert", "dbert_ai"),
    ("library", "gemma2"),
    ("library", "llama3.2"),
    ("library", "qwen2.5"),
    ("library", "phi3"),
}

# Download Safety Limits (Audit #MODEL-001)
MAX_MODEL_DOWNLOAD_BYTES = 16 * 1024 * 1024 * 1024  # 16 GB max

# Manifest media types
MEDIA_TYPE_MODEL = "application/vnd.ollama.image.model"
MEDIA_TYPE_SYSTEM = "application/vnd.ollama.image.system"
MEDIA_TYPE_PARAMS = "application/vnd.ollama.image.params"


class OllamaPullError(Exception):
    """Error pulling model from Ollama registry."""


def validate_model_allowlist(namespace: str, name: str) -> None:
    """Validate model against approved catalog allowlist (Audit #MODEL-002)."""
    key = (namespace.strip().lower(), name.strip().lower())
    if key not in APPROVED_MODELS:
        raise OllamaPullError(
            f"Model '{namespace}/{name}' is not in the approved model allowlist (Audit #MODEL-002)."
        )


def validate_hardware_compatibility(size_bytes: int) -> tuple[bool, str]:
    """Verify system has sufficient RAM/headroom to load model (Audit #MODEL-003)."""
    try:
        from core.hardware import detect_hardware
        hw = detect_hardware()
        free_mb = hw.ram_free_mb
        required_mb = (size_bytes / (1024 * 1024)) + 500  # model + 500MB KV cache buffer
        if free_mb > 0 and free_mb < required_mb:
            return False, f"Insufficient free RAM ({free_mb}MB available, {int(required_mb)}MB required)"
        return True, "OK"
    except Exception as exc:
        return True, f"Hardware validation bypassed: {exc}"


class ModelManifest:
    """Parsed Ollama manifest with cryptographic signature support."""

    def __init__(self, digest: str, layers: list[dict], config: dict, raw_data: dict | None = None):
        self.digest = digest
        self.layers = layers
        self.config = config
        self.raw_data = raw_data or {}

    @property
    def model_blob(self) -> dict | None:
        """The GGUF model layer."""
        for layer in self.layers:
            if layer.get("mediaType") == MEDIA_TYPE_MODEL:
                return layer
        return None

    @property
    def system_blob(self) -> dict | None:
        """The chat template layer."""
        for layer in self.layers:
            if layer.get("mediaType") == MEDIA_TYPE_SYSTEM:
                return layer
        return None

    @property
    def params_blob(self) -> dict | None:
        """The model params layer."""
        for layer in self.layers:
            if layer.get("mediaType") == MEDIA_TYPE_PARAMS:
                return layer
        return None

    @classmethod
    def from_dict(cls, data: dict) -> ModelManifest:
        """Parse from Ollama manifest API response."""
        return cls(
            digest=data.get("config", {}).get("digest", ""),
            layers=data.get("layers", []),
            config=data.get("config", {}),
            raw_data=data,
        )

    def verify_signature(self, public_key_b64: str) -> bool:
        """Verify the cryptographic signature of the manifest using an Ed25519 public key."""
        from core.security.signatures import ManifestVerifier
        return ManifestVerifier.verify_manifest(self.raw_data, public_key_b64)


def _get_manifest(namespace: str, name: str, tag: str) -> ModelManifest:
    """Fetch and parse the Ollama manifest for a model.

    Args:
        namespace: Model namespace (e.g. "DBERT")
        name: Model name (e.g. "DBERT_AI")
        tag: Model tag (e.g. "latest")

    Returns:
        Parsed ModelManifest

    Raises:
        OllamaPullError: If manifest fetch fails
    """
    import httpx

    url = f"{OLLAMA_REGISTRY}/v2/{namespace}/{name}/manifests/{tag}"
    headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}

    logger.info(f"Fetching manifest: {url}")
    response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)

    if response.status_code != 200:
        raise OllamaPullError(
            f"Failed to fetch manifest: HTTP {response.status_code} — {response.text[:300]}"
        )

    try:
        data = response.json()
        manifest = ModelManifest.from_dict(data)
        logger.info(
            f"Manifest: {len(manifest.layers)} layers "
            f"(model={manifest.model_blob is not None}, "
            f"system={manifest.system_blob is not None}, "
            f"params={manifest.params_blob is not None})"
        )
        return manifest
    except Exception as exc:
        raise OllamaPullError(f"Failed to parse manifest: {exc}") from exc


def _get_blob_url(namespace: str, name: str, digest: str) -> str:
    """Build the download URL for a blob."""
    return f"{OLLAMA_REGISTRY}/v2/{namespace}/{name}/blobs/{digest}"


def _verify_sha256(filepath: Path, expected_digest: str) -> bool:
    """Verify a file's sha256 digest.

    Args:
        filepath: Path to file
        expected_digest: Expected sha256 digest (with or without 'sha256:' prefix)

    Returns:
        True if digest matches
    """
    expected = expected_digest.replace("sha256:", "")
    h = hashlib.sha256()

    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)

    actual = h.hexdigest()
    matches = actual == expected

    if matches:
        logger.info(f"Digest verified: {filepath.name} ({filepath.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        logger.error(f"Digest mismatch: expected {expected[:16]}..., got {actual[:16]}...")

    return matches


def check_disk_space(
    dest_dir: Path,
    required_bytes: int,
    safety_margin_bytes: int = 100 * 1024 * 1024,
) -> None:
    """Validate that dest_dir has sufficient free disk space before downloading (Audit #59).

    Args:
        dest_dir: Directory where files will be stored.
        required_bytes: Total expected download size in bytes.
        safety_margin_bytes: Safety headroom in bytes (default 100 MB).

    Raises:
        OllamaPullError: If available free space is less than required + safety margin.
    """
    import shutil
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        usage = shutil.disk_usage(dest)
        total_needed = required_bytes + safety_margin_bytes
        if usage.free < total_needed:
            free_mb = usage.free / (1024 * 1024)
            needed_mb = total_needed / (1024 * 1024)
            req_mb = required_bytes / (1024 * 1024)
            margin_mb = safety_margin_bytes / (1024 * 1024)
            raise OllamaPullError(
                f"Insufficient disk space in '{dest}': requires {req_mb:.1f} MB + "
                f"{margin_mb:.1f} MB safety margin ({needed_mb:.1f} MB total), "
                f"but only {free_mb:.1f} MB is available."
            )
    except OSError as exc:
        logger.warning(f"Could not check disk usage for {dest}: {exc}")


def save_model_metadata(
    dest_dir: Path,
    model_file: str,
    digest: str,
    namespace: str,
    name: str,
    tag: str,
    size_bytes: int,
    has_chat_template: bool = False,
    has_params: bool = False,
) -> Path:
    """Persist verified installation metadata alongside the model (Audit #44)."""
    import json
    from datetime import datetime, timezone
    meta = {
        "namespace": namespace,
        "name": name,
        "tag": tag,
        "file_name": model_file,
        "digest": digest,
        "size_bytes": size_bytes,
        "has_chat_template": has_chat_template,
        "has_params": has_params,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_path = Path(dest_dir) / f"{model_file}.meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"Saved model metadata: {meta_path}")
    return meta_path


def get_model_metadata(
    dest_dir: Path | None = None,
    model_file: str | None = None,
) -> dict | None:
    """Retrieve persisted model installation metadata if present (Audit #44)."""
    import json
    from core.config import LOCAL_MODEL_FILE, MODELS_DIR
    dest = Path(dest_dir) if dest_dir else MODELS_DIR
    fname = model_file or LOCAL_MODEL_FILE
    meta_path = dest / f"{fname}.meta.json"
    if not meta_path.exists():
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to read model metadata from {meta_path}: {exc}")
        return None


def cleanup_partial_downloads(dest_dir: Path | None = None) -> list[str]:
    """Clean up any leftover .part files in dest_dir (Audit #41)."""
    from core.config import MODELS_DIR
    dest = Path(dest_dir) if dest_dir else MODELS_DIR
    cleaned = []
    if dest.exists():
        for p in dest.glob("*.part"):
            try:
                p.unlink(missing_ok=True)
                cleaned.append(p.name)
                logger.info(f"Removed partial download: {p.name}")
            except Exception as exc:
                logger.warning(f"Failed to remove partial download {p.name}: {exc}")
    return cleaned


def _download_blob(
    url: str,
    dest: Path,
    expected_digest: str,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> None:
    """Download a blob with resumable Range requests, .part isolation, and digest verification.

    Audit #40: Validates Content-Range header start offset on HTTP 206 responses.
    Audit #41: Writes to a .part file and atomically renames only after digest verification.

    Args:
        url: Download URL
        dest: Destination file path
        expected_digest: Expected sha256 digest
        progress_callback: Optional callback(label, downloaded, total)
    """
    import os
    import httpx

    # If destination already exists and matches expected digest, skip download
    if dest.exists():
        if _verify_sha256(dest, expected_digest):
            logger.info(f"Blob already exists and verified: {dest.name}")
            return
        logger.warning(f"Existing file {dest.name} failed digest check, will re-download")
        dest.unlink(missing_ok=True)

    # Use a .part temporary file while downloading to avoid exposing partial/corrupt files (Audit #41)
    part_file = dest.with_name(dest.name + ".part")
    downloaded = 0
    headers = {}

    # Check for resumable partial download
    if part_file.exists():
        downloaded = part_file.stat().st_size
        if downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
            logger.info(f"Resuming download: {downloaded / 1024 / 1024:.1f} MB already downloaded in .part")

    try:
        with httpx.stream("GET", url, headers=headers, timeout=300.0, follow_redirects=True) as response:
            if response.status_code == 200:
                # Full download from start
                mode = "wb"
                downloaded = 0
                total = int(response.headers.get("content-length", 0))
                logger.info(f"Downloading: {url.split('/')[-1][:40]} ({total / 1024 / 1024:.1f} MB)")
            elif response.status_code == 206:
                # Resume accepted — validate Content-Range header (Audit #40)
                content_range = response.headers.get("content-range", "").strip()
                range_start = None
                total = 0
                if content_range.lower().startswith("bytes "):
                    spec = content_range[6:].strip()
                    if "/" in spec:
                        range_part, total_str = spec.split("/", 1)
                        if "-" in range_part:
                            s_str = range_part.split("-")[0]
                            if s_str.isdigit():
                                range_start = int(s_str)
                        if total_str.isdigit():
                            total = int(total_str)

                # Validate Content-Range start matches downloaded offset
                if range_start is not None and range_start != downloaded:
                    logger.warning(
                        f"Content-Range start mismatch: expected {downloaded}, server returned {range_start}. "
                        "Resetting partial file and restarting full download."
                    )
                    mode = "wb"
                    downloaded = 0
                else:
                    mode = "ab"
                    logger.info(f"Resuming from {downloaded / 1024 / 1024:.1f} MB")
            elif response.status_code == 416:
                # Range not satisfiable — partial file may be corrupt or offset exceeds size
                logger.warning(f"HTTP 416 Range Not Satisfiable for {part_file.name}. Truncating and re-downloading.")
                part_file.unlink(missing_ok=True)
                mode = "wb"
                downloaded = 0
                with httpx.stream("GET", url, timeout=300.0, follow_redirects=True) as full_resp:
                    if full_resp.status_code != 200:
                        raise OllamaPullError(f"HTTP {full_resp.status_code} on re-download: {full_resp.text[:200]}")
                    total = int(full_resp.headers.get("content-length", 0))
                    with open(part_file, "wb") as f:
                        for chunk in full_resp.iter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback("model", downloaded, total)
                    response = full_resp
            else:
                raise OllamaPullError(f"HTTP {response.status_code}: {response.text[:200]}")

            if response.status_code in (200, 206):
                with open(part_file, mode) as f:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback("model", downloaded, total)

    except httpx.HTTPStatusError as exc:
        raise OllamaPullError(f"Download failed: HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise OllamaPullError(f"Download failed: {exc}") from exc

    logger.info(f"Download complete: {downloaded / 1024 / 1024:.1f} MB")

    # Verify digest on the downloaded .part file before promoting
    if not _verify_sha256(part_file, expected_digest):
        part_file.unlink(missing_ok=True)
        raise OllamaPullError(f"Digest verification failed for {part_file.name}")

    # Atomically promote verified partial file to destination (Audit #41)
    os.replace(part_file, dest)
    logger.info(f"Atomically promoted verified blob to {dest}")


def pull_model(
    namespace: str = DEFAULT_MODEL_NAMESPACE,
    name: str = DEFAULT_MODEL_NAME,
    tag: str = DEFAULT_MODEL_TAG,
    dest_dir: Path | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    require_signed_manifest: bool = False,
    trusted_public_keys: list[str] | None = None,
) -> dict:
    """Pull a model from the Ollama registry.

    Args:
        namespace: Model namespace (e.g. "DBERT")
        name: Model name (e.g. "DBERT_AI")
        tag: Model tag (e.g. "latest")
        dest_dir: Destination directory (default: MODELS_DIR/dbert_ai)
        progress_callback: Optional callback(label, downloaded, total)

    Returns:
        Dict with model info: {namespace, name, tag, path, size_mb, digest}

    Raises:
        OllamaPullError: If any step fails
    """
    # Validate against approved model allowlist (Audit #MODEL-002)
    validate_model_allowlist(namespace, name)

    from core.config import LOCAL_MODEL_FILE, MODELS_DIR

    dest_dir = dest_dir or MODELS_DIR
    # Destination path traversal guard (Audit #MODEL-001)
    if ".." in dest_dir.parts:
        raise OllamaPullError(f"Target destination '{dest_dir}' contains path traversal (Audit #MODEL-001)")

    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Pulling {namespace}/{name}:{tag} -> {dest_dir}")

    # 1. Fetch manifest
    manifest = _get_manifest(namespace, name, tag)

    # 1b. Cryptographic signature check for signed model manifests (Audit #MODEL-001)
    if require_signed_manifest:
        from core.security.signatures import ManifestVerifier
        sig_meta = manifest.raw_data.get("signature")
        if not sig_meta:
            raise OllamaPullError("Model manifest is unsigned; rejected under strict integrity policy")
        valid, key_used = ManifestVerifier.verify_against_trust_anchors(
            manifest.raw_data.get("raw_bytes") or bytes(str(manifest.digest), "utf-8"),
            sig_meta.get("value", ""),
            trusted_keys=trusted_public_keys,
        )
        if not valid:
            # Fallback check verifying canonical manifest dictionary
            if not any(manifest.verify_signature(k) for k in (trusted_public_keys or [])):
                raise OllamaPullError("Model manifest cryptographic signature verification failed (Audit #MODEL-001)")
        logger.info("Model manifest signature verified successfully against trusted key")

    # Preflight disk space and size limit checks before starting download (Audit #59 & #MODEL-001)
    total_required = sum(int(l.get("size", 0)) for l in manifest.layers if "size" in l)
    if total_required > MAX_MODEL_DOWNLOAD_BYTES:
        raise OllamaPullError(
            f"Model size ({total_required // (1024*1024)}MB) exceeds maximum download limit of {MAX_MODEL_DOWNLOAD_BYTES // (1024*1024)}MB (Audit #MODEL-001)"
        )
    check_disk_space(dest_dir, total_required)

    # Hardware compatibility validation (Audit #MODEL-003)
    compat_ok, compat_msg = validate_hardware_compatibility(total_required)
    if not compat_ok:
        raise OllamaPullError(f"Hardware compatibility check failed: {compat_msg} (Audit #MODEL-003)")

    # 2. Download model blob (GGUF)
    model_blob = manifest.model_blob
    if model_blob is None:
        raise OllamaPullError("No model blob in manifest")

    model_digest = model_blob["digest"]
    model_url = _get_blob_url(namespace, name, model_digest)
    model_path = dest_dir / LOCAL_MODEL_FILE

    def _model_progress(label: str, downloaded: int, total: int):
        if progress_callback:
            progress_callback(label, downloaded, total)

    _download_blob(model_url, model_path, model_digest, _model_progress)

    # 3. Download system blob (chat template) if present
    system_blob = manifest.system_blob
    if system_blob:
        system_digest = system_blob["digest"]
        system_url = _get_blob_url(namespace, name, system_digest)
        system_path = dest_dir / "chat_template.txt"
        _download_blob(system_url, system_path, system_digest)
        logger.info(f"Chat template saved: {system_path}")
    else:
        logger.info("No chat template in manifest (using default)")

    # 4. Download params blob if present
    params_blob = manifest.params_blob
    if params_blob:
        params_digest = params_blob["digest"]
        params_url = _get_blob_url(namespace, name, params_digest)
        params_path = dest_dir / "params.json"
        _download_blob(params_url, params_path, params_digest)
        logger.info(f"Params saved: {params_path}")
    else:
        logger.info("No params in manifest (using defaults)")

    size_mb = model_path.stat().st_size / 1024 / 1024
    logger.info(f"Pull complete: {model_path} ({size_mb:.1f} MB)")

    # 5. Persist verified model metadata (Audit #44)
    save_model_metadata(
        dest_dir=dest_dir,
        model_file=LOCAL_MODEL_FILE,
        digest=model_digest,
        namespace=namespace,
        name=name,
        tag=tag,
        size_bytes=model_path.stat().st_size,
        has_chat_template=system_blob is not None,
        has_params=params_blob is not None,
    )

    return {
        "namespace": namespace,
        "name": name,
        "tag": tag,
        "path": str(model_path),
        "size_mb": round(size_mb, 1),
        "digest": model_digest,
        "has_chat_template": system_blob is not None,
        "has_params": params_blob is not None,
    }


def check_model_available(namespace: str = DEFAULT_MODEL_NAMESPACE,
                          name: str = DEFAULT_MODEL_NAME,
                          tag: str = DEFAULT_MODEL_TAG) -> dict:
    """Check if a model is available without downloading.

    Returns:
        Dict with availability info: {available, size_mb, layers, ...}
    """
    try:
        manifest = _get_manifest(namespace, name, tag)
        model_blob = manifest.model_blob

        if model_blob is None:
            return {"available": False, "reason": "No model blob in manifest"}

        size_str = model_blob.get("size", "0")
        try:
            size_bytes = int(size_str)
            size_mb = size_bytes / 1024 / 1024
        except (ValueError, TypeError):
            size_mb = 0

        return {
            "available": True,
            "namespace": namespace,
            "name": name,
            "tag": tag,
            "size_mb": round(size_mb, 1),
            "layers": len(manifest.layers),
            "digest": model_blob["digest"],
        }
    except Exception as exc:
        return {
            "available": False,
            "reason": str(exc)[:200],
        }
