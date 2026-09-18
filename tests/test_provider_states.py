"""Tests for PROVIDER-002 (ProviderStatus), PROVIDER-003 (Capability-aware routing), and PROVIDER-004 (Catalog caching)."""

from core.providers.base import (
    LLMProvider,
    ModelInfo,
    SpeedTier,
    Capability,
    ProviderStatus,
    ChatResponse,
)
from core.providers.registry import ProviderRegistry


class MockTestProvider(LLMProvider):
    def __init__(self, key: str, name: str, is_auth: bool = True, is_reach: bool = True):
        self._key = key
        self._name = name
        self._is_auth = is_auth
        self._is_reach = is_reach
        self.fetch_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def key(self) -> str:
        return self._key

    @property
    def is_authenticated(self) -> bool:
        return self._is_auth

    @property
    def is_reachable(self) -> bool:
        return self._is_reach

    def validate_key(self) -> tuple[bool, str]:
        return (True, "OK") if self._is_auth else (False, "No key")

    def list_models(self) -> list[ModelInfo]:
        self.fetch_count += 1
        return [
            ModelInfo(
                id=f"{self._key}-fast",
                name=f"{self._name} Fast",
                provider=self._key,
                speed_tier=SpeedTier.FAST,
                capabilities=[Capability.CHAT, Capability.TOOLS],
                context_length=8192,
            ),
            ModelInfo(
                id=f"{self._key}-slow",
                name=f"{self._name} Slow",
                provider=self._key,
                speed_tier=SpeedTier.SLOW,
                capabilities=[Capability.CHAT, Capability.VISION],
                context_length=32768,
            ),
        ]

    def chat(self, messages, options=None):
        return ChatResponse(text="test", model_id="test", provider=self._key)

    def stream(self, messages, options=None):
        yield "test"


def test_provider_status_enum():
    """PROVIDER-002: Verify ProviderStatus reports correctly."""
    p_ready = MockTestProvider("p1", "Ready Provider", is_auth=True, is_reach=True)
    assert p_ready.get_status() == ProviderStatus.READY

    p_unauth = MockTestProvider("p2", "Unauth Provider", is_auth=False, is_reach=True)
    assert p_unauth.get_status() == ProviderStatus.AUTH_REQUIRED

    p_offline = MockTestProvider("p3", "Offline Provider", is_auth=True, is_reach=False)
    assert p_offline.get_status() == ProviderStatus.OFFLINE


def test_model_catalog_caching():
    """PROVIDER-004: Verify TTL catalog caching prevents repeated fetch."""
    p = MockTestProvider("p1", "Cached Provider")
    assert p.fetch_count == 0

    m1 = p.get_cached_models(ttl_seconds=60.0)
    assert p.fetch_count == 1
    assert len(m1) == 2

    # Second call uses cache
    m2 = p.get_cached_models(ttl_seconds=60.0)
    assert p.fetch_count == 1
    assert m1 == m2


def test_capability_aware_routing(monkeypatch):
    """PROVIDER-003: Verify fallback chain filters by capability and context length."""
    reg = ProviderRegistry()
    p = MockTestProvider("local", "Local Provider")
    reg.register(p)

    # Allow local in tests
    monkeypatch.setattr("core.settings.get_settings", lambda: {"privacy_mode": "local_only"})

    # Require TOOLS
    chain_tools = reg.get_fallback_chain(
        preferred_tier=SpeedTier.FAST,
        required_capabilities=[Capability.TOOLS],
    )
    assert len(chain_tools) == 1
    assert chain_tools[0][1].id == "local-fast"

    # Require VISION
    chain_vision = reg.get_fallback_chain(
        preferred_tier=SpeedTier.SLOW,
        required_capabilities=[Capability.VISION],
    )
    assert len(chain_vision) == 1
    assert chain_vision[0][1].id == "local-slow"

    # Require impossible context length
    chain_huge = reg.get_fallback_chain(
        preferred_tier=SpeedTier.FAST,
        min_context_length=65536,
    )
    assert len(chain_huge) == 0
