"""Tests for Phase 10 — Model Integration & Prompt Contracts."""
from __future__ import annotations

import pytest

from core.prompts.loader import PromptContractLoader, get_prompt_loader
from core.inference.service import InferenceService, ModelConfig, get_inference_service
from core.runtimes.chemistry import _build_chemistry_system_prompt
from core.runtimes.general import _build_general_system_prompt


class TestPromptContractLoader:
    def test_load_chemistry_prompt_contract(self):
        loader = get_prompt_loader()
        prompt = loader.load_prompt("chemistry_tutor_system_v1.txt")
        assert len(prompt) > 0
        assert "Gayatri Chemistry Tutor" in prompt

    def test_load_general_prompt_contract(self):
        loader = get_prompt_loader()
        prompt = loader.load_prompt("general_assistant_system_v1.txt")
        assert len(prompt) > 0
        assert "Gayatri AI" in prompt

    def test_nonexistent_prompt_fallback(self, tmp_path):
        loader = PromptContractLoader(prompts_dir=tmp_path)
        prompt = loader.load_prompt("missing.txt")
        assert prompt == ""


class TestInferenceService:
    def test_inference_service_config(self):
        service = get_inference_service()
        assert service.config.family == "gayatri-tutor"
        assert service.config.provider == "local"

    def test_custom_model_config(self):
        config = ModelConfig(family="qwen2.5", model_id="qwen2.5-0.5b-gguf", quantization="Q4_0")
        service = InferenceService(config=config)
        assert service.config.model_id == "qwen2.5-0.5b-gguf"
        assert service.config.quantization == "Q4_0"


class TestRuntimeSystemPromptsWithContracts:
    def test_chemistry_system_prompt_with_contract(self):
        prompt = _build_chemistry_system_prompt(["Thermodynamics"])
        assert "Gayatri Chemistry Tutor" in prompt
        assert "Thermodynamics" in prompt

    def test_general_system_prompt_with_contract(self):
        prompt = _build_general_system_prompt(is_chemistry_redirect=True)
        assert "Gayatri AI" in prompt
        assert "MODE BOUNDARY" in prompt
