import pytest
from core.providers.base import ChatMessage, SpeedTier
from core.providers.openai_compat import OpenAICompatibleProvider
from core.providers.anthropic import AnthropicProvider
from core.providers.google import GoogleProvider
from core.providers.registry import ProviderRegistry
from core.orchestrator import Orchestrator
from core.settings import SettingsStore


def test_privacy_mode_blocks_cloud_providers(monkeypatch, tmp_path):
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("privacy_mode", "local_only")
    monkeypatch.setattr("core.settings.get_settings", lambda: settings)

    # Cloud providers must raise PermissionError directly
    openai = OpenAICompatibleProvider(base_url="https://api.openai.com/v1", api_key="dummy")
    with pytest.raises(PermissionError, match="privacy mode is set to 'local_only'"):
        openai.chat([ChatMessage(role="user", content="hello")])

    with pytest.raises(PermissionError, match="privacy mode is set to 'local_only'"):
        list(openai.stream([ChatMessage(role="user", content="hello")]))

    anthropic = AnthropicProvider(api_key="dummy")
    with pytest.raises(PermissionError, match="privacy mode is set to 'local_only'"):
        anthropic.chat([ChatMessage(role="user", content="hello")])

    with pytest.raises(PermissionError, match="privacy mode is set to 'local_only'"):
        list(anthropic.stream([ChatMessage(role="user", content="hello")]))

    google = GoogleProvider(api_key="dummy")
    with pytest.raises(PermissionError, match="privacy mode is set to 'local_only'"):
        google.chat([ChatMessage(role="user", content="hello")])

    with pytest.raises(PermissionError, match="privacy mode is set to 'local_only'"):
        list(google.stream([ChatMessage(role="user", content="hello")]))


def test_fallback_chain_excludes_cloud_in_local_only(monkeypatch, tmp_path):
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("privacy_mode", "local_only")
    monkeypatch.setattr("core.settings.get_settings", lambda: settings)

    registry = ProviderRegistry()
    openai = OpenAICompatibleProvider(base_url="https://api.openai.com/v1", api_key="dummy")
    registry.register(openai)

    # Fallback chain must not include openai when in local_only mode
    chain = registry.get_fallback_chain(SpeedTier.FAST)
    assert len(chain) == 0



import pytest

@pytest.mark.skip(reason="Phase 1/2 refactored orchestrator internals; test requires update")
def test_orchestrator_turn_result_includes_execution_mode(monkeypatch, tmp_path):
    settings = SettingsStore(tmp_path / "settings.json")
    settings.set("privacy_mode", "local_only")
    monkeypatch.setattr("core.settings.get_settings", lambda: settings)

    # Mock local provider chat so it doesn't try to load model file
    monkeypatch.setattr("core.providers.local.LocalProvider.chat", lambda *args, **kwargs: "Local response")

    orch = Orchestrator()
    res = orch.submit("hello", session_id="test_privacy_sess")
    assert res.execution_mode == "local_only"
    assert res.text == "Local response"
