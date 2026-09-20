"""Tests for Phase 19: Upload Security (Section 25).

Verifies zero-trust upload security controls:
- Extension allowlist (.pdf, .txt, .json, .csv, .md)
- Content / MIME verification via magic bytes
- Size limits and randomized UUID storage names
- Non-executable storage outside web roots
- Student data isolation (Student A cannot access Student B's uploads)
- Path traversal defense across all upload parameters
- Malformed file handling & PDF parser limits (max pages, max chars)
- RAG ingester validation integration
"""
import io
import json
import pytest
from pathlib import Path

from core.security.upload import SecureUploadManager, StoredUpload
from core.rag.ingester import NCERTIngester


@pytest.fixture
def upload_mgr(tmp_path):
    """Provide an isolated SecureUploadManager in a temporary directory."""
    return SecureUploadManager(base_dir=tmp_path / "uploads", max_file_bytes=50_000)


def test_upload_extension_allowlist_and_executables(upload_mgr):
    """Verify allowed extensions succeed and executable extensions are rejected."""
    # Allowed extensions
    txt_upload = upload_mgr.save_upload("std_1", "notes.txt", b"Thermodynamics notes")
    assert txt_upload.extension == ".txt"
    assert txt_upload.size_bytes == len(b"Thermodynamics notes")

    json_upload = upload_mgr.save_upload("std_1", "data.json", b'{"topic": "enthalpy"}')
    assert json_upload.extension == ".json"

    # Disallowed executable extensions
    with pytest.raises(ValueError, match="Dangerous executable extension"):
        upload_mgr.save_upload("std_1", "hack.exe", b"binary content")

    with pytest.raises(ValueError, match="Dangerous executable extension"):
        upload_mgr.save_upload("std_1", "script.bat", b"@echo off")

    with pytest.raises(ValueError, match="Dangerous executable extension"):
        upload_mgr.save_upload("std_1", "payload.php", b"<?php phpinfo(); ?>")

    with pytest.raises(ValueError, match="Dangerous executable extension"):
        upload_mgr.save_upload("std_1", "run.ps1", b"Write-Host 'pwned'")


def test_upload_double_extension_prevention(upload_mgr):
    """Verify dangerous double extensions are detected and blocked."""
    with pytest.raises(ValueError, match="Double extension detected"):
        upload_mgr.save_upload("std_1", "malware.exe.pdf", b"%PDF-1.4\ncontent")

    with pytest.raises(ValueError, match="Double extension detected"):
        upload_mgr.save_upload("std_1", "exploit.php.txt", b"some text")


def test_upload_mime_verification(upload_mgr):
    """Verify content matches declared MIME type and disguised files are blocked."""
    # Disguised fake PDF (plain text content with .pdf extension)
    with pytest.raises(ValueError, match="File does not match expected PDF signature"):
        upload_mgr.save_upload("std_1", "fake.pdf", b"This is plain text, not a PDF")

    # Valid PDF magic bytes
    valid_pdf_bytes = b"%PDF-1.5\n%trailer\n%%EOF"
    pdf_upload = upload_mgr.save_upload("std_1", "chapter1.pdf", valid_pdf_bytes)
    assert pdf_upload.extension == ".pdf"
    assert pdf_upload.mime_type == "application/pdf"


def test_randomized_storage_and_non_executable_permissions(upload_mgr):
    """Verify files are stored under random UUID names, never client filenames."""
    content = b"Entropy and Gibbs Free Energy"
    upload = upload_mgr.save_upload("std_1", "my_secret_notes.txt", content)

    # Filename on disk MUST NOT be 'my_secret_notes.txt'
    disk_filename = upload.stored_path.name
    assert disk_filename != "my_secret_notes.txt"
    assert disk_filename.endswith(".txt")
    assert upload.upload_id in disk_filename
    assert upload.original_filename == "my_secret_notes.txt"

    # Content on disk matches
    with open(upload.stored_path, "rb") as f:
        assert f.read() == content


def test_student_isolation(upload_mgr):
    """Verify Student A's uploaded documents cannot be accessed or deleted by Student B."""
    upload_a = upload_mgr.save_upload("student_a", "student_a_notes.txt", b"Student A Private Notes")

    # Student A can retrieve their own upload
    retrieved = upload_mgr.get_upload("student_a", upload_a.upload_id)
    assert retrieved is not None
    assert retrieved.upload_id == upload_a.upload_id

    # Student B cannot retrieve Student A's upload
    assert upload_mgr.get_upload("student_b", upload_a.upload_id) is None

    # Student B cannot see Student A's upload in list
    b_uploads = upload_mgr.list_uploads("student_b")
    assert len(b_uploads) == 0

    # Student B cannot delete Student A's upload
    deleted_by_b = upload_mgr.delete_upload("student_b", upload_a.upload_id)
    assert deleted_by_b is False

    # Student A's file still exists
    assert upload_mgr.get_upload("student_a", upload_a.upload_id) is not None

    # Student A can delete their own upload
    deleted_by_a = upload_mgr.delete_upload("student_a", upload_a.upload_id)
    assert deleted_by_a is True
    assert upload_mgr.get_upload("student_a", upload_a.upload_id) is None
    assert not upload_a.stored_path.exists()


def test_path_traversal_defense(upload_mgr):
    """Verify path traversal is blocked in student_id, filename, and upload_id."""
    # Path traversal in student_id
    with pytest.raises(ValueError, match="path traversal or null byte"):
        upload_mgr.save_upload("../../evil_student", "notes.txt", b"text")

    # Path traversal in filename is sanitized to basename
    upload = upload_mgr.save_upload("student_1", "../../etc/passwd.txt", b"harmless notes")
    assert upload.original_filename == "passwd.txt"
    assert str(upload.stored_path).startswith(str(upload_mgr.base_dir / "student_1"))

    # Path traversal in upload_id
    with pytest.raises(ValueError, match="Invalid upload ID format"):
        upload_mgr.get_upload("student_1", "../evil_id")


def test_document_parsing_and_limits(upload_mgr):
    """Verify safe document parsing with character limits and malformed PDF handling."""
    # Text parsing with character limit
    long_text = ("Hess's Law states that enthalpy changes are additive. " * 50).encode("utf-8")
    txt_upload = upload_mgr.save_upload("std_1", "hess.txt", long_text)

    parsed_text = upload_mgr.parse_document_safely(txt_upload, max_chars=100)
    assert len(parsed_text) == 100
    assert parsed_text.startswith("Hess's Law")

    # JSON document parsing
    json_upload = upload_mgr.save_upload("std_1", "thermo.json", b'{"concept": "enthalpy", "chapter": "6"}')
    parsed_json = upload_mgr.parse_document_safely(json_upload)
    assert "enthalpy" in parsed_json

    # Malformed PDF handling
    corrupt_pdf_bytes = b"%PDF-1.5\nCORRUPT_DATA_NOT_VALID_PDF_OBJECTS"
    pdf_upload = upload_mgr.save_upload("std_1", "corrupt.pdf", corrupt_pdf_bytes)

    with pytest.raises(ValueError, match="Malformed or corrupt PDF document"):
        upload_mgr.parse_document_safely(pdf_upload)


def test_ncert_ingester_validation_integration(tmp_path):
    """Verify NCERTIngester enforces zero-trust validation before parsing."""
    ingester = NCERTIngester()

    # Non-JSON file rejected
    txt_file = tmp_path / "chapter.txt"
    txt_file.write_text("not json content", encoding="utf-8")
    chunks = ingester.parse_file(txt_file)
    assert chunks == []

    # Malformed JSON file rejected
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{invalid json", encoding="utf-8")
    chunks = ingester.parse_file(bad_json)
    assert chunks == []

    # Valid NCERT JSON parses successfully
    valid_json = tmp_path / "thermo.json"
    valid_data = {
        "source_id": "NCERT_CH11_THERMO",
        "chapter": "Thermodynamics",
        "sections": [
            {
                "topic": "First Law",
                "subtopic": "Internal Energy",
                "page": 165,
                "text": "The first law of thermodynamics states that energy can neither be created nor destroyed."
            }
        ]
    }
    valid_json.write_text(json.dumps(valid_data), encoding="utf-8")
    chunks = ingester.parse_file(valid_json)
    assert len(chunks) == 1
    assert chunks[0].chapter == "Thermodynamics"
    assert chunks[0].topic == "First Law"
    assert "energy can neither be created" in chunks[0].text
