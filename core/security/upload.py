"""Gayatri AI — Secure Upload & Ingestion Manager (Section 25).

Enforces zero-trust upload security across the application:
- Extension allowlist (.pdf, .txt, .json, .csv, .md)
- Content / MIME verification via magic bytes
- Strict size limits (default 10 MB)
- Randomized, unguessable storage names (UUID + content hash)
- Non-executable storage located outside web roots
- Student data isolation (uploads strictly scoped per student_id)
- Malformed file handling & PDF parser limits (max pages, max chars)
- Invariant: Never execute uploaded content.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.config import UPLOADS_DIR
from core.security.validation import (
    DEFAULT_MAX_FILE_BYTES,
    validate_json,
    validate_student_id,
    validate_uploaded_file,
)

logger = logging.getLogger("gayatri.security.upload")

# Regex to validate upload_id: 32 hex chars from uuid4
_UPLOAD_ID_REGEX = re.compile(r"^[a-f0-9]{32}$")

DEFAULT_MAX_PAGES = 100
DEFAULT_MAX_EXTRACTED_CHARS = 500_000


@dataclass
class StoredUpload:
    """Represents a securely stored file upload."""
    upload_id: str
    student_id: str
    original_filename: str
    stored_path: Path
    extension: str
    size_bytes: int
    mime_type: str
    sha256_hash: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stored_path"] = str(self.stored_path)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> StoredUpload:
        return cls(
            upload_id=data["upload_id"],
            student_id=data["student_id"],
            original_filename=data["original_filename"],
            stored_path=Path(data["stored_path"]),
            extension=data["extension"],
            size_bytes=data["size_bytes"],
            mime_type=data["mime_type"],
            sha256_hash=data["sha256_hash"],
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            metadata=data.get("metadata", {}),
        )


class SecureUploadManager:
    """Manages student-scoped file uploads with strict security controls."""

    def __init__(
        self,
        base_dir: Path | None = None,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ):
        self.base_dir = (base_dir or UPLOADS_DIR).resolve()
        self.max_file_bytes = max_file_bytes
        self._lock = threading.RLock()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_student_dir(self, student_id: str) -> Path:
        """Resolve and validate student-scoped upload directory, preventing path traversal."""
        clean_student_id = validate_student_id(student_id)
        student_dir = (self.base_dir / clean_student_id).resolve()
        if not str(student_dir).startswith(str(self.base_dir)):
            raise ValueError(f"Path traversal detected in student directory: {student_dir}")
        student_dir.mkdir(parents=True, exist_ok=True)
        return student_dir

    def _get_index_path(self, student_id: str) -> Path:
        """Get the path to the student's upload metadata index."""
        student_dir = self._get_student_dir(student_id)
        return student_dir / "_uploads_index.json"

    def _load_student_index(self, student_id: str) -> dict[str, StoredUpload]:
        """Load the upload index for a student."""
        index_path = self._get_index_path(student_id)
        if not index_path.exists():
            return {}
        try:
            with open(index_path, encoding="utf-8") as f:
                data = json.load(f)
            uploads = {}
            for uid, record in data.items():
                try:
                    uploads[uid] = StoredUpload.from_dict(record)
                except Exception as rec_err:
                    logger.warning(f"Skipping corrupt upload index entry {uid}: {rec_err}")
            return uploads
        except Exception as exc:
            logger.error(f"Failed to read upload index for student {student_id}: {exc}")
            return {}

    def _save_student_index(self, student_id: str, index: dict[str, StoredUpload]) -> None:
        """Save the upload index for a student atomically."""
        index_path = self._get_index_path(student_id)
        temp_path = index_path.with_suffix(".tmp")
        data = {uid: upload.to_dict() for uid, upload in index.items()}
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_path.replace(index_path)

    def save_upload(
        self,
        student_id: str,
        filename: str,
        content_or_stream: Any,
        max_bytes: int | None = None,
        metadata: dict | None = None,
    ) -> StoredUpload:
        """Validate, store, and record a student upload.

        - Validates student_id against path traversal and character rules
        - Validates file extension, double extensions, size limit, and MIME magic bytes
        - Stores file under a random UUID-derived name, never the client filename
        - Sets non-executable file permissions
        - Isolates storage in a student-specific directory
        """
        clean_student_id = validate_student_id(student_id)
        max_allowed_bytes = max_bytes or self.max_file_bytes

        # Zero-trust validation of incoming file
        validated = validate_uploaded_file(
            filename=filename,
            content_or_stream=content_or_stream,
            max_bytes=max_allowed_bytes,
        )

        content: bytes = validated["content"]
        extension: str = validated["extension"]
        mime_type: str = validated["mime_type"]
        size_bytes: int = validated["size_bytes"]
        clean_filename: str = validated["filename"]

        upload_id = uuid.uuid4().hex
        sha256_hash = hashlib.sha256(content).hexdigest()

        # Random, unguessable storage filename: {uuid}_{hash[:8]}{ext}
        stored_filename = f"{upload_id}_{sha256_hash[:8]}{extension}"

        with self._lock:
            student_dir = self._get_student_dir(clean_student_id)
            stored_path = (student_dir / stored_filename).resolve()

            if not str(stored_path).startswith(str(student_dir)):
                raise ValueError(f"Path traversal detected in stored path: {stored_path}")

            # Write file content
            with open(stored_path, "wb") as f:
                f.write(content)

            # Set non-executable permissions (read/write only)
            try:
                os.chmod(stored_path, 0o600)
            except Exception as chmod_err:
                logger.debug(f"Could not set 0o600 permissions on {stored_path}: {chmod_err}")

            upload_record = StoredUpload(
                upload_id=upload_id,
                student_id=clean_student_id,
                original_filename=clean_filename,
                stored_path=stored_path,
                extension=extension,
                size_bytes=size_bytes,
                mime_type=mime_type,
                sha256_hash=sha256_hash,
                metadata=metadata or {},
            )

            # Update index
            index = self._load_student_index(clean_student_id)
            index[upload_id] = upload_record
            self._save_student_index(clean_student_id, index)

            logger.info(
                f"Securely saved upload {upload_id} for student '{clean_student_id}' "
                f"({clean_filename} -> {stored_filename}, {size_bytes} bytes)"
            )
            return upload_record

    def get_upload(self, student_id: str, upload_id: str) -> StoredUpload | None:
        """Retrieve a stored upload for a student, ensuring ownership and existence."""
        clean_student_id = validate_student_id(student_id)
        clean_upload_id = str(upload_id).strip()

        if not _UPLOAD_ID_REGEX.match(clean_upload_id):
            raise ValueError(f"Invalid upload ID format: '{clean_upload_id}'")

        with self._lock:
            index = self._load_student_index(clean_student_id)
            upload = index.get(clean_upload_id)
            if not upload:
                return None

            # Verify file exists on disk
            if not upload.stored_path.exists():
                logger.warning(f"Upload file {upload.stored_path} missing on disk for ID {clean_upload_id}")
                return None

            return upload

    def list_uploads(self, student_id: str) -> list[StoredUpload]:
        """List all valid uploads for a student."""
        clean_student_id = validate_student_id(student_id)
        with self._lock:
            index = self._load_student_index(clean_student_id)
            valid_uploads = []
            for upload in index.values():
                if upload.stored_path.exists():
                    valid_uploads.append(upload)
            return valid_uploads

    def delete_upload(self, student_id: str, upload_id: str) -> bool:
        """Securely delete an upload and remove its metadata."""
        clean_student_id = validate_student_id(student_id)
        clean_upload_id = str(upload_id).strip()

        if not _UPLOAD_ID_REGEX.match(clean_upload_id):
            raise ValueError(f"Invalid upload ID format: '{clean_upload_id}'")

        with self._lock:
            index = self._load_student_index(clean_student_id)
            if clean_upload_id not in index:
                return False

            upload = index.pop(clean_upload_id)
            if upload.stored_path.exists():
                try:
                    upload.stored_path.unlink()
                except Exception as unlink_err:
                    logger.error(f"Failed to delete upload file {upload.stored_path}: {unlink_err}")

            self._save_student_index(clean_student_id, index)
            logger.info(f"Deleted upload {clean_upload_id} for student '{clean_student_id}'")
            return True

    def parse_document_safely(
        self,
        stored_upload: StoredUpload,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_chars: int = DEFAULT_MAX_EXTRACTED_CHARS,
    ) -> str:
        """Safely extract plain text from an uploaded document with strict parser limits.

        Defends against:
        - PDF bombs / infinite recursion
        - Decompression bombs
        - Memory exhaustion
        - Corrupted or malformed file streams
        """
        path = stored_upload.stored_path
        if not path.exists():
            raise FileNotFoundError(f"Stored document file not found: {path}")

        ext = stored_upload.extension.lower()

        if ext in (".txt", ".md", ".csv"):
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read(max_chars + 1)
                if len(content) > max_chars:
                    logger.warning(f"Document {path.name} truncated to {max_chars} characters")
                    content = content[:max_chars]
                return content
            except Exception as exc:
                raise ValueError(f"Failed to read text document: {exc}") from exc

        elif ext == ".json":
            try:
                with open(path, encoding="utf-8") as f:
                    raw = f.read()
                data = validate_json(raw, max_size_bytes=self.max_file_bytes)
                formatted = json.dumps(data, indent=2)
                return formatted[:max_chars]
            except Exception as exc:
                raise ValueError(f"Failed to parse JSON document: {exc}") from exc

        elif ext == ".pdf":
            return self._parse_pdf_safely(path, max_pages=max_pages, max_chars=max_chars)

        else:
            raise ValueError(f"Unsupported document extension for parsing: '{ext}'")

    def _parse_pdf_safely(
        self,
        path: Path,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_chars: int = DEFAULT_MAX_EXTRACTED_CHARS,
    ) -> str:
        """Safely parse PDF documents using PyMuPDF (fitz) with page and character caps."""
        try:
            import fitz
        except ImportError:
            # Fallback when fitz is not installed
            logger.warning("PyMuPDF (fitz) not available; falling back to raw stream read")
            with open(path, "rb") as f:
                raw_bytes = f.read(max_chars)
            return raw_bytes.decode("utf-8", errors="replace")[:max_chars]

        try:
            doc = fitz.open(str(path))
        except Exception as open_err:
            raise ValueError(f"Malformed or corrupt PDF document: {open_err}") from open_err

        try:
            if doc.is_encrypted:
                raise ValueError("Encrypted PDF documents are not supported")

            total_pages = len(doc)
            pages_to_read = min(total_pages, max_pages)

            extracted_chunks: list[str] = []
            total_chars = 0

            for page_num in range(pages_to_read):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text() or ""
                except Exception as page_err:
                    logger.warning(f"Error extracting page {page_num} of {path.name}: {page_err}")
                    continue

                extracted_chunks.append(page_text)
                total_chars += len(page_text)
                if total_chars >= max_chars:
                    logger.warning(f"PDF {path.name} reached maximum character limit of {max_chars}")
                    break

            full_text = "\n\n".join(extracted_chunks)
            if len(full_text) > max_chars:
                full_text = full_text[:max_chars]

            return full_text
        finally:
            doc.close()
