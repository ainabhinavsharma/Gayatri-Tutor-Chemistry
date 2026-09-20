"""Tests for Phase 18: Zero-Trust Input Validation (Section 24).

Verifies strict input validation across application boundaries:
- Student IDs, Session IDs, Concept IDs, Question IDs
- Query and prompt lengths, null byte detection
- JSON payload parsing, size limits, and required keys
- File extension allowlists, double extension prevention, size limits, MIME magic bytes
- Orchestrator and ProgressService boundary enforcement
"""
import io
import json
import pytest
from core.security.validation import (
    validate_student_id,
    validate_session_id,
    validate_concept_id,
    validate_question_id,
    validate_query_text,
    validate_prompt_text,
    validate_json,
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
    validate_uploaded_file,
)
from core.orchestrator import Orchestrator, TurnOptions
from core.learning.progress import ProgressService
from core.tutor.state import TutorStateManager


def test_student_id_validation():
    """Verify student ID allowlist and security boundary checks."""
    # Valid IDs
    assert validate_student_id("student_123") == "student_123"
    assert validate_student_id("user@test.org") == "user@test.org"
    assert validate_student_id("student-chem.45") == "student-chem.45"

    # Invalid IDs: traversal, null bytes, SQL/shell injection, whitespace
    with pytest.raises(ValueError, match="path traversal or null byte"):
        validate_student_id("../student_evil")

    with pytest.raises(ValueError, match="path traversal or null byte"):
        validate_student_id("student\x00evil")

    with pytest.raises(ValueError, match="Invalid student ID"):
        validate_student_id("student; DROP TABLE students;--")

    with pytest.raises(ValueError, match="Invalid student ID"):
        validate_student_id("student$(whoami)")

    with pytest.raises(ValueError, match="Invalid student ID"):
        validate_student_id("student with spaces")

    with pytest.raises(ValueError, match="student_id must not be empty"):
        validate_student_id("")

    with pytest.raises(ValueError, match="length must be between 1 and 64"):
        validate_student_id("a" * 65)


def test_session_id_validation():
    """Verify session ID security checks."""
    # Valid IDs
    assert validate_session_id("sess_12345") == "sess_12345"
    assert validate_session_id("uuid-1234-abcd:chem") == "uuid-1234-abcd:chem"

    # Invalid IDs
    with pytest.raises(ValueError, match="path traversal or null byte"):
        validate_session_id("../../sess_evil")

    with pytest.raises(ValueError, match="path traversal or null byte"):
        validate_session_id("sess\x00id")

    with pytest.raises(ValueError, match="Invalid session ID"):
        validate_session_id("sess/slash")

    with pytest.raises(ValueError, match="length must be between 1 and 128"):
        validate_session_id("")

    with pytest.raises(ValueError, match="length must be between 1 and 128"):
        validate_session_id("s" * 129)


def test_concept_and_question_id_validation():
    """Verify concept and question ID formatting."""
    # Concept IDs
    assert validate_concept_id("thermo.first_law") == "thermo.first_law"
    assert validate_concept_id("inorganic.atomic_structure") == "inorganic.atomic_structure"

    with pytest.raises(ValueError, match="Invalid concept ID"):
        validate_concept_id("concept with space")

    with pytest.raises(ValueError, match="path traversal or null byte"):
        validate_concept_id("../concept")

    # Question IDs
    assert validate_question_id("q_thermo_001") == "q_thermo_001"
    assert validate_question_id("chem-exam-2024.q12") == "chem-exam-2024.q12"

    with pytest.raises(ValueError, match="Invalid question ID"):
        validate_question_id("q; DROP TABLE questions;")


def test_query_and_prompt_text_validation():
    """Verify query and prompt text bounds and null byte detection."""
    # Valid query
    assert validate_query_text("What is Hess's law?") == "What is Hess's law?"

    # Empty query
    with pytest.raises(ValueError, match="Query text must not be empty"):
        validate_query_text("   ")

    # Null byte in query
    with pytest.raises(ValueError, match="forbidden null bytes"):
        validate_query_text("Query with \x00 null byte")

    # Query length limit
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        validate_query_text("A" * 4001)

    # Prompt length limit
    assert len(validate_prompt_text("P" * 10000)) == 10000
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        validate_prompt_text("P" * 32001)


def test_json_validation():
    """Verify JSON size limit, structure parsing, and required keys."""
    # Valid JSON
    valid_payload = '{"student_id": "std_1", "concept_id": "thermo.gibbs", "score": 0.9}'
    parsed = validate_json(valid_payload, required_keys=["student_id", "concept_id"])
    assert parsed["student_id"] == "std_1"
    assert parsed["score"] == 0.9

    # Missing required key
    with pytest.raises(ValueError, match="is missing required keys"):
        validate_json(valid_payload, required_keys=["student_id", "missing_key"])

    # Malformed JSON
    with pytest.raises(ValueError, match="Malformed JSON payload"):
        validate_json('{"student_id": "std_1", invalid}')

    # Payload exceeding size limit
    huge_json = json.dumps({"data": "x" * 1_000_001})
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        validate_json(huge_json, max_bytes=1_000_000)


def test_file_validation():
    """Verify file extension allowlist, double-extension blocks, and MIME checks."""
    # Allowed extension
    assert validate_file_extension("notes.pdf") == ".pdf"
    assert validate_file_extension("data.json") == ".json"
    assert validate_file_extension("chem.csv") == ".csv"

    # Disallowed executable extensions
    with pytest.raises(ValueError, match="Dangerous executable extension"):
        validate_file_extension("script.exe")

    with pytest.raises(ValueError, match="Dangerous executable extension"):
        validate_file_extension("run.bat")

    # Double extensions
    with pytest.raises(ValueError, match="Double extension detected"):
        validate_file_extension("malware.exe.txt")

    with pytest.raises(ValueError, match="Double extension detected"):
        validate_file_extension("exploit.php.pdf")

    # File size limit
    validate_file_size(1024, max_bytes=2048)
    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        validate_file_size(3000, max_bytes=2048)

    # MIME / Magic bytes verification
    pdf_content = b"%PDF-1.5\nfake pdf content"
    assert validate_mime_type(pdf_content, ".pdf") == "application/pdf"

    fake_pdf = b"not a real pdf content"
    with pytest.raises(ValueError, match="does not match expected PDF signature"):
        validate_mime_type(fake_pdf, ".pdf")

    json_content = b'{"chem": "thermo"}'
    assert validate_mime_type(json_content, ".json") == "application/json"

    # Full uploaded file helper
    stream = io.BytesIO(pdf_content)
    res = validate_uploaded_file("chapter1.pdf", stream, max_bytes=10000)
    assert res["filename"] == "chapter1.pdf"
    assert res["mime_type"] == "application/pdf"
    assert res["size_bytes"] == len(pdf_content)


def test_orchestrator_and_progress_validation_integration():
    """Verify orchestrator and progress service enforce validation boundaries."""
    orch = Orchestrator()

    # Orchestrator submit with path traversal in session_id
    res = orch.submit("What is enthalpy?", session_id="../evil_sess")
    assert res.status == "ERROR"
    assert res.routing_reason == "input_validation_failed"

    # Orchestrator submit with path traversal in student_id
    opts = TurnOptions(student_id="../../evil_student")
    res = orch.submit("What is enthalpy?", session_id="good_sess", options=opts)
    assert res.status == "ERROR"
    assert res.routing_reason == "input_validation_failed"

    # Orchestrator stream with path traversal in session_id
    stream_gen = orch.stream("What is enthalpy?", session_id="../evil_stream")
    tokens = list(stream_gen)
    assert len(tokens) == 1
    assert tokens[0][1] is True  # is_last=True
    assert "path traversal" in tokens[0][0]

    # ProgressService rejects invalid IDs
    state_mgr = TutorStateManager(":memory:")
    progress_svc = ProgressService(state_mgr)

    with pytest.raises(ValueError, match="path traversal or null byte"):
        progress_svc.get_concept_progress("../evil_std", "thermo.first_law")

    with pytest.raises(ValueError, match="path traversal or null byte"):
        progress_svc.get_concept_progress("student_1", "../evil_concept")

    with pytest.raises(ValueError, match="path traversal or null byte"):
        progress_svc.get_student_progress_summary("../evil_std")
