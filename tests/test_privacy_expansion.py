"""Tests for Indian PII expansion, Verhoeff/Luhn checksum verification, and credential redaction (Batch F)."""

from core.privacy import PIIRedactor, validate_verhoeff, validate_luhn
from core.logging_setup import _redact


class TestIndianPIIAndChecksums:
    def setup_method(self):
        self.redactor = PIIRedactor(enabled=True)

    def test_verhoeff_validation(self):
        """Audit #94: Verhoeff algorithm accurately validates 12-digit Aadhaar numbers."""
        assert validate_verhoeff("2345 6789 0124") is True
        assert validate_verhoeff("2345-6789-0124") is True
        assert validate_verhoeff("234567890124") is True

        # Invalid checksum
        assert validate_verhoeff("2345 6789 0123") is False
        # Starting with 0 or 1 is invalid in UIDAI Aadhaar specification
        assert validate_verhoeff("0123 4567 8901") is False
        assert validate_verhoeff("1234 5678 9012") is False
        # Wrong length
        assert validate_verhoeff("2345 6789 012") is False

    def test_luhn_validation(self):
        """Audit #95: Luhn algorithm validates credit cards and filters out non-card integers."""
        assert validate_luhn("4111 1111 1111 1111") is True
        assert validate_luhn("4111-1111-1111-1111") is True
        assert validate_luhn("4111111111111111") is True

        # Corrupt check digit
        assert validate_luhn("4111 1111 1111 1112") is False
        # Arbitrary integer not satisfying Luhn
        assert validate_luhn("1234 5678 1234 5678") is False

    def test_aadhaar_redaction_and_restore(self):
        """Audit #94: Valid Aadhaar numbers are redacted and restorable; invalid ones are left intact."""
        text = "My Aadhaar is 2345 6789 0124 and another is 2345-6789-0124 but fake is 2345 6789 0123."
        res = self.redactor.redact(text)

        assert res.has_pii is True
        assert "2345 6789 0124" not in res.clean_text
        assert "2345-6789-0124" not in res.clean_text
        # Fake Aadhaar with invalid checksum must NOT be redacted
        assert "2345 6789 0123" in res.clean_text
        assert "[AADHAAR_" in res.clean_text

        # Restore
        restored = res.restore(res.clean_text)
        assert restored == text

    def test_pan_redaction_and_restore(self):
        """Audit #94: Indian PAN cards (5 letters, 4 digits, 1 letter) are redacted and restorable."""
        text = "Tax ID is ABCDE1234F and student PAN is BNZPK9876Q."
        res = self.redactor.redact(text)

        assert res.has_pii is True
        assert "ABCDE1234F" not in res.clean_text
        assert "BNZPK9876Q" not in res.clean_text
        assert "[PAN_" in res.clean_text

        restored = res.restore(res.clean_text)
        assert restored == text

    def test_indian_passport_redaction_and_restore(self):
        """Audit #94: Indian Passport numbers (1 letter followed by 7 digits) are redacted and restorable."""
        text = "Passport number: A1234567, renewal: Z9876543."
        res = self.redactor.redact(text)

        assert res.has_pii is True
        assert "A1234567" not in res.clean_text
        assert "Z9876543" not in res.clean_text
        assert "[PASSPORT_IN_" in res.clean_text

        restored = res.restore(res.clean_text)
        assert restored == text

    def test_upi_id_redaction_and_restore(self):
        """Audit #94: Indian UPI IDs (Virtual Payment Addresses) are redacted and restorable."""
        text = "Pay via UPI to rahul@oksbi or merchant 9876543210@paytm or team@ybl."
        res = self.redactor.redact(text)

        assert res.has_pii is True
        assert "rahul@oksbi" not in res.clean_text
        assert "9876543210@paytm" not in res.clean_text
        assert "team@ybl" not in res.clean_text
        assert "[UPI_ID_" in res.clean_text

        restored = res.restore(res.clean_text)
        assert restored == text

    def test_credit_card_luhn_redaction(self):
        """Audit #95: Valid credit cards are redacted; invalid checksums are preserved."""
        text = "Valid card: 4111 1111 1111 1111, invalid card: 4111 1111 1111 1112."
        res = self.redactor.redact(text)

        assert res.has_pii is True
        assert "4111 1111 1111 1111" not in res.clean_text
        assert "4111 1111 1111 1112" in res.clean_text
        assert "[CREDIT_CARD_" in res.clean_text

        restored = res.restore(res.clean_text)
        assert restored == text

    def test_anthropic_credential_log_redaction(self):
        """Audit #92: Anthropic API keys (sk-ant-...) with hyphens are redacted."""
        secret = "sk-ant-api03-abcdef1234567890abcdef1234567890-XYZ"
        log_msg = f"Connecting with key: {secret}"
        redacted = _redact(log_msg)
        assert secret not in redacted
        assert "[REDACTED]" in redacted
