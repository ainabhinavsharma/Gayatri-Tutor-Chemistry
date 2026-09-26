"""Gayatri AI — Web Research Policy (P11-T01).

Manages policy settings controlling network search egress.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from core.settings import get_settings

logger = logging.getLogger("gayatri.research.policy")


@dataclass
class ResearchPolicy:
    """Policy settings controlling web search egress."""
    enabled: bool = False
    max_results: int = 3
    timeout_seconds: float = 5.0
    allowed_domains: list[str] = None

    @classmethod
    def from_settings(cls) -> ResearchPolicy:
        """Create policy evaluated against global privacy settings."""
        settings = get_settings()
        privacy_mode = settings.get("privacy_mode", "local_only")
        cloud_allowed = (privacy_mode == "cloud_allowed")

        policy = cls(
            enabled=cloud_allowed,
            max_results=3,
            timeout_seconds=5.0,
        )
        logger.info(f"Research Policy evaluated: enabled={policy.enabled} (privacy_mode={privacy_mode})")
        return policy
