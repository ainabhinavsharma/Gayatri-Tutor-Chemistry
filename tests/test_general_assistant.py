"""Tests for Phase 8 — General Assistant."""
from __future__ import annotations

import pytest

from core.runtimes.general import (
    GeneralAssistantRuntime,
    _build_general_system_prompt,
    _detect_chemistry_tutoring_request,
)


class TestGeneralAssistantRuntime:
    def test_build_system_prompt_contains_capabilities(self):
        prompt = _build_general_system_prompt(is_chemistry_redirect=False)
        assert "Gayatri AI" in prompt
        assert "Writing & Editing" in prompt
        assert "Summarization" in prompt
        assert "Brainstorming & Planning" in prompt
        assert "MODE BOUNDARY" not in prompt

    def test_build_system_prompt_with_chemistry_redirect(self):
        prompt = _build_general_system_prompt(is_chemistry_redirect=True)
        assert "MODE BOUNDARY" in prompt
        assert "Chemistry Tutor" in prompt

    def test_detect_chemistry_tutoring_request(self):
        assert _detect_chemistry_tutoring_request("teach me chemistry thermodynamics") is True
        assert _detect_chemistry_tutoring_request("balance chemical equation Na + H2O") is True
        assert _detect_chemistry_tutoring_request("give me a chemistry quiz") is True
        assert _detect_chemistry_tutoring_request("Write a poem about rain") is False
        assert _detect_chemistry_tutoring_request("Summarize this article for me") is False

    def test_runtime_initialization(self):
        rt = GeneralAssistantRuntime()
        assert rt is not None
