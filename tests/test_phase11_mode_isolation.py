"""Tests for Phase 11: Mode Isolation Re-Audit (P10-T10)."""
import pytest
from core.mode import AppMode, InvalidAppModeError, validate_app_mode, get_mode_policy


def test_valid_app_modes():
    """Test valid AppMode strings and enum instances."""
    assert validate_app_mode("chemistry_tutor") == AppMode.CHEMISTRY_TUTOR
    assert validate_app_mode("GENERAL_ASSISTANT") == AppMode.GENERAL_ASSISTANT
    assert validate_app_mode(AppMode.CHEMISTRY_TUTOR) == AppMode.CHEMISTRY_TUTOR


def test_invalid_app_mode_rejection():
    """Test that invalid app modes raise InvalidAppModeError."""
    with pytest.raises(InvalidAppModeError):
        validate_app_mode("invalid_mode_name")

    with pytest.raises(InvalidAppModeError):
        validate_app_mode("")

    with pytest.raises(InvalidAppModeError):
        validate_app_mode("admin_mode")


def test_mode_policies():
    """Test mode policy feature flags for Chemistry Tutor vs General Assistant."""
    chem_policy = get_mode_policy("chemistry_tutor")
    assert chem_policy.chemistry_only is True
    assert chem_policy.rag is True
    assert chem_policy.assessment is True
    assert chem_policy.adaptive_learning is True
    assert chem_policy.controlled_web_fallback is True

    gen_policy = get_mode_policy(AppMode.GENERAL_ASSISTANT)
    assert gen_policy.chemistry_only is False
    assert gen_policy.rag is False
    assert gen_policy.assessment is False
    assert gen_policy.adaptive_learning is False
    assert gen_policy.controlled_web_fallback is False
