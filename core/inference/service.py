"""Gayatri AI — Unified Inference Service (P10-T01).

Model abstraction layer ensuring both ChemistryTutorRuntime and GeneralAssistantRuntime
route inference through a single unified engine configuration.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Optional

logger = logging.getLogger("gayatri.inference.service")


@dataclass
class ModelConfig:
    """Configuration for local model engine."""
    provider: str = "local"
    family: str = "qwen2.5"
    model_id: str = "qwen2.5-1.5b-instruct-gguf"
    quantization: str = "Q4_K_M"
    context_length: int = 4096


class InferenceService:
    """Unified model inference service for all runtime modes."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()

    def stream_chat(self, messages: list[dict[str, str]], max_tokens: int = 400) -> Iterator[str]:
        """Stream chat tokens from the configured model engine."""
        try:
            from legacy.agents.default_agents import _local_chat_stream
            logger.info(
                f"InferenceService streaming chat: family={self.config.family}, "
                f"model_id={self.config.model_id}, max_tokens={max_tokens}"
            )
            return _local_chat_stream(messages, max_tokens=max_tokens)
        except Exception as exc:
            logger.error(f"InferenceService stream_chat error: {exc}")
            raise


_global_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    global _global_service
    if _global_service is None:
        _global_service = InferenceService()
    return _global_service
