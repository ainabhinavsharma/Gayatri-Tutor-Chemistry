"""Gayatri AI — Prompt Contract Loader.

Loads versioned text prompt contracts from training/prompts/.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("gayatri.prompts.loader")

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "training" / "prompts"


class PromptContractLoader:
    """Loads versioned system prompt contracts from disk."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self._dir = prompts_dir or _PROMPTS_DIR
        self._cache: dict[str, str] = {}

    def load_prompt(self, name: str) -> str:
        """Load a prompt template by filename (e.g. 'chemistry_tutor_system_v1.txt')."""
        if name in self._cache:
            return self._cache[name]

        file_path = self._dir / name
        if not file_path.exists():
            logger.warning(f"Prompt contract file not found: {file_path}. Using fallback.")
            return ""

        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()

        self._cache[name] = content
        logger.info(f"Loaded prompt contract: {name} ({len(content)} chars)")
        return content


_global_loader: Optional[PromptContractLoader] = None


def get_prompt_loader() -> PromptContractLoader:
    global _global_loader
    if _global_loader is None:
        _global_loader = PromptContractLoader()
    return _global_loader
