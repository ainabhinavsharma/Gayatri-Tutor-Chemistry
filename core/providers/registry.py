"""Gayatri AI — Provider registry + unified model catalog.

Manages all LLM providers, fetches their models, and provides a single
unified view of every available model across all configured providers.
"""

from __future__ import annotations

import logging

from core.providers.base import Capability, LLMProvider, ModelInfo, SpeedTier

logger = logging.getLogger("gayatri.providers.registry")


class ProviderRegistry:
    """Registry of LLM providers with unified model catalog.

    Usage:
        registry = ProviderRegistry()
        registry.register(OpenAIProvider(api_key=...))
        registry.register(AnthropicProvider(api_key=...))

        # Get all models across all providers
        all_models = registry.get_all_models()

        # Get models for a specific provider
        openai_models = registry.get_models("openai")
    """

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        """Register a provider. Idempotent — safe to call multiple times."""
        self._providers[provider.key] = provider
        logger.info(f"Provider registered: {provider.name} ({provider.key})")

    def unregister(self, provider_key: str) -> None:
        """Remove a provider."""
        self._providers.pop(provider_key, None)
        logger.info(f"Provider unregistered: {provider_key}")

    def get(self, provider_key: str) -> LLMProvider | None:
        """Get a provider by key."""
        return self._providers.get(provider_key)

    def list_providers(self) -> list[dict]:
        """List all registered providers with their status."""
        result = []
        for key, provider in self._providers.items():
            result.append({
                "key": key,
                "name": provider.name,
                "available": self._check_provider_available(provider),
            })
        return result

    def _check_provider_available(self, provider: LLMProvider) -> bool:
        """Quick check if a provider is ready and reachable."""
        try:
            if hasattr(provider, "is_ready"):
                return provider.is_ready()
            return provider.is_authenticated and provider.is_reachable
        except Exception:
            return False

    def get_models(self, provider_key: str) -> list[ModelInfo]:
        """Get models for a specific provider."""
        provider = self._providers.get(provider_key)
        if provider is None:
            return []
        try:
            return provider.list_models()
        except Exception as exc:
            logger.error(f"Failed to fetch models for {provider_key}: {exc}")
            return []

    def get_all_models(self) -> list[ModelInfo]:
        """Get all models from all providers, sorted by provider then name."""
        all_models: list[ModelInfo] = []
        for provider in self._providers.values():
            try:
                models = provider.list_models()
                all_models.extend(models)
            except Exception as exc:
                logger.error(f"Failed to fetch models from {provider.name}: {exc}")
        all_models.sort(key=lambda m: (m.provider, m.id))
        return all_models

    def get_models_by_speed(self, speed_tier: SpeedTier) -> list[ModelInfo]:
        """Get all models matching a speed tier."""
        return [m for m in self.get_all_models() if m.speed_tier == speed_tier]

    def get_models_by_capability(self, capability: Capability) -> list[ModelInfo]:
        """Get all models supporting a specific capability."""
        return [m for m in self.get_all_models() if capability in m.capabilities]

    def get_fallback_chain(
        self,
        preferred_tier: SpeedTier,
        required_capabilities: list[Capability] | None = None,
        min_context_length: int = 0,
    ) -> list[tuple[LLMProvider, ModelInfo]]:
        """Get a fallback chain of (provider, model) pairs for a tier.

        Order: preferred_tier → medium → slow.
        Filters by required capabilities and minimum context length (Audit #PROVIDER-003).
        Returns available providers only.
        Respects privacy_mode: in LOCAL_ONLY mode, only local providers are included.
        """
        # Check privacy mode
        try:
            from core.config import ExecutionMode
            from core.settings import get_settings
            mode_str = get_settings().get("privacy_mode", "local_only")
            exec_mode = ExecutionMode(mode_str)
        except Exception:
            exec_mode = None  # fail safe — allow only local

        chain: list[tuple[LLMProvider, ModelInfo]] = []
        seen = set()

        tier_order = [preferred_tier, SpeedTier.MEDIUM, SpeedTier.SLOW]

        for tier in tier_order:
            for provider in self._providers.values():
                if provider.key in seen:
                    continue
                # Enforce LOCAL_ONLY: skip cloud providers
                if (exec_mode is None or exec_mode == ExecutionMode.LOCAL_ONLY) and provider.key != "local":
                    logger.debug(f"Skipping cloud provider '{provider.key}' — privacy mode is local_only")
                    continue
                # Ensure provider is actually ready before adding to fallback chain (Audit #26)
                if not self._check_provider_available(provider):
                    logger.debug(f"Skipping provider '{provider.key}' — not ready/available")
                    continue
                try:
                    models = provider.list_models()
                    matching = [
                        m for m in models
                        if m.speed_tier == tier
                        and (not required_capabilities or all(c in m.capabilities for c in required_capabilities))
                        and (m.context_length >= min_context_length)
                    ]
                    if matching:
                        chain.append((provider, matching[0]))
                        seen.add(provider.key)
                except Exception:
                    continue

        return chain

    def to_catalog_dict(self) -> list[dict]:
        """Return the full model catalog as a list of dicts (for JSON serialization)."""
        return [m.to_dict() for m in self.get_all_models()]


def _register_default_providers(registry: ProviderRegistry) -> None:
    """Pre-register default providers using stored keys if available."""
    try:
        from core.providers.local import LocalLLMProvider
        if registry.get("local") is None:
            registry.register(LocalLLMProvider())
    except Exception as exc:
        logger.warning(f"Could not register default local provider: {exc}")

    google_key = ""
    anthropic_key = ""
    openai_key = ""
    try:
        from core.security.secrets import get_vault
        vault = get_vault()
        google_key = vault.retrieve_key("google") or ""
        anthropic_key = vault.retrieve_key("anthropic") or ""
        openai_key = vault.retrieve_key("openai") or ""
    except Exception as exc:
        logger.debug(f"Could not retrieve keys from vault during default registration: {exc}")

    try:
        from core.providers.google import GoogleProvider
        if registry.get("google") is None:
            registry.register(GoogleProvider(api_key=google_key))
    except Exception as exc:
        logger.warning(f"Could not register default Google provider: {exc}")

    try:
        from core.providers.anthropic import AnthropicProvider
        if registry.get("anthropic") is None:
            registry.register(AnthropicProvider(api_key=anthropic_key))
    except Exception as exc:
        logger.warning(f"Could not register default Anthropic provider: {exc}")

    try:
        from core.providers.openai_compat import OpenAICompatibleProvider
        if registry.get("openai") is None:
            registry.register(
                OpenAICompatibleProvider(
                    name="OpenAI",
                    key="openai",
                    base_url="https://api.openai.com/v1",
                    api_key=openai_key,
                )
            )
    except Exception as exc:
        logger.warning(f"Could not register default OpenAI provider: {exc}")


# Global registry (lazy-initialized)
_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _register_default_providers(_registry)
    return _registry
