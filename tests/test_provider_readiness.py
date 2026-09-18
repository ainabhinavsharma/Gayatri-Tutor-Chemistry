"""Tests for Batch B: Provider readiness, capability integrity, and TurnOptions routing.

Verifies fixes for Audit issues:
- #20: Provider Registry treats fallback model catalogs as available
- #21: Cloud model catalogs are hardcoded and can become stale (live discovery & fallback distinction)
- #22: Google provider claims tool support but tool calls are not converted
- #23: Anthropic provider's JSON mode API contract
- #24: Provider model selection ignores user model selection (model_override & forced_tier)
- #25: TurnOptions.task_type appears unused
- #26: Provider registry fallback chain can select an unready provider
"""

from unittest.mock import MagicMock, patch

from core.orchestrator import Orchestrator, TurnOptions
from core.providers.anthropic import AnthropicProvider
from core.providers.base import (
    Capability,
    CatalogSource,
    ChatMessage,
    ChatOptions,
    ChatResponse,
    LLMProvider,
    ModelInfo,
    SpeedTier,
)
from core.providers.google import GoogleProvider
from core.providers.openai_compat import OpenAICompatibleProvider
from core.providers.registry import ProviderRegistry
from core.settings import SettingsStore


class TestProviderReadinessAndAvailability:
    """Audit #20 & #26: Unready providers with fallback catalogs must not be considered available."""

    def test_empty_key_providers_are_not_ready_or_available(self):
        reg = ProviderRegistry()
        google = GoogleProvider(api_key="")
        anthropic = AnthropicProvider(api_key="")
        openai = OpenAICompatibleProvider(api_key="", base_url="https://api.openai.com/v1")

        reg.register(google)
        reg.register(anthropic)
        reg.register(openai)

        # Fallback models exist in catalog
        assert len(google.list_models()) > 0
        assert len(anthropic.list_models()) > 0
        assert len(openai.list_models()) > 0

        # But providers are NOT authenticated, NOT ready, and NOT available
        assert not google.is_authenticated
        assert not google.is_ready()
        assert not reg._check_provider_available(google)

        assert not anthropic.is_authenticated
        assert not anthropic.is_ready()
        assert not reg._check_provider_available(anthropic)

        assert not openai.is_authenticated
        assert not openai.is_ready()
        assert not reg._check_provider_available(openai)

    def test_fallback_chain_strictly_excludes_unready_cloud_providers(self, monkeypatch, tmp_path):
        settings = SettingsStore(tmp_path / "settings.json")
        settings.set("privacy_mode", "cloud_allowed")
        monkeypatch.setattr("core.settings.get_settings", lambda: settings)

        reg = ProviderRegistry()
        # Providers with empty keys
        google = GoogleProvider(api_key="")
        anthropic = AnthropicProvider(api_key="")
        openai = OpenAICompatibleProvider(api_key="", base_url="https://api.openai.com/v1")

        reg.register(google)
        reg.register(anthropic)
        reg.register(openai)

        # Even though cloud_allowed, unready providers must not enter fallback chain
        chain = reg.get_fallback_chain(SpeedTier.FAST)
        assert len(chain) == 0

        chain_medium = reg.get_fallback_chain(SpeedTier.MEDIUM)
        assert len(chain_medium) == 0

    def test_catalog_source_marked_live_vs_fallback(self):
        # Without network/keys, catalog source is FALLBACK
        google = GoogleProvider(api_key="")
        models = google.list_models()
        assert google.catalog_source == CatalogSource.FALLBACK
        for m in models:
            assert m.catalog_source == CatalogSource.FALLBACK

        # Mock successful API call for Google
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "models/gemini-2.0-flash", "displayName": "Gemini 2.0 Flash"},
            ]
        }

        with patch("httpx.get", return_value=mock_response):
            live_google = GoogleProvider(api_key="valid-test-key")
            live_models = live_google.list_models()
            assert live_google.catalog_source == CatalogSource.LIVE
            assert live_google.is_authenticated
            assert live_google.is_reachable
            assert live_google.is_ready()
            assert live_models[0].catalog_source == CatalogSource.LIVE


class TestProviderCapabilitiesAndContracts:
    """Audit #22 & #23: Correct capabilities and API contracts."""

    def test_google_provider_does_not_claim_unsupported_tools(self):
        google = GoogleProvider(api_key="dummy")
        assert google.supports_tools() is False

        for model in google.list_models():
            assert model.supports_tools is False
            assert Capability.TOOLS not in model.capabilities

    def test_anthropic_json_mode_contract_and_capabilities(self, monkeypatch, tmp_path):
        settings = SettingsStore(tmp_path / "settings.json")
        settings.set("privacy_mode", "cloud_allowed")
        monkeypatch.setattr("core.settings.get_settings", lambda: settings)

        anthropic = AnthropicProvider(api_key="dummy-key")
        assert anthropic.supports_json() is False
        for model in anthropic.list_models():
            assert model.supports_json is False

        # Verify chat payload does NOT send response_format={"type": "json_object"}
        captured_payload = {}

        def mock_post(url, headers=None, json=None, timeout=None):
            nonlocal captured_payload
            captured_payload = json
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "content": [{"type": "text", "text": '{"result": "ok"}'}],
                "usage": {"input_tokens": 10, "output_tokens": 10},
                "model": "claude-3-5-sonnet-20241022",
                "stop_reason": "stop",
            }
            return mock_resp

        with patch("httpx.post", side_effect=mock_post):
            anthropic.chat(
                messages=[ChatMessage(role="user", content="Return JSON")],
                options=ChatOptions(json_mode=True),
            )

        assert "response_format" not in captured_payload
        assert "Respond strictly with valid JSON" in captured_payload.get("system", "")


class TestOrchestratorTurnOptionsRouting:
    """Audit #24 & #25: Observable behavior for task_type, model_override, and forced_tier."""

    def test_turn_options_task_type_direct_agent_dispatch(self, monkeypatch):
        monkeypatch.setattr("core.providers.local.LocalProvider.chat_stream", lambda *args, **kwargs: iter(["Mock answer"]))
        orch = Orchestrator()
        # Submit a generic message with task_type="tutor"
        # Normally "tell me something" wouldn't match Tutor triggers
        res = orch.submit("tell me something", options=TurnOptions(task_type="tutor"))
        assert res.agent_name == "Tutor"
        assert "task_type:tutor" in res.routing_reason

        # Test task_type="code"
        res_code = orch.submit("look at this text", options=TurnOptions(task_type="code"))
        assert res_code.agent_name == "Code Reviewer"
        assert "task_type:code" in res_code.routing_reason

    def test_turn_options_model_override_privacy_mode_enforcement(self, monkeypatch, tmp_path):
        settings = SettingsStore(tmp_path / "settings.json")
        settings.set("privacy_mode", "local_only")
        monkeypatch.setattr("core.settings.get_settings", lambda: settings)

        orch = Orchestrator()
        # Requesting a cloud model override while in LOCAL_ONLY mode must be blocked cleanly
        res = orch.submit("hello", options=TurnOptions(model_override="openai/gpt-4o"))
        assert "Operation blocked by privacy policy" in res.text
        assert "PermissionError" in res.routing_reason

    def test_turn_options_model_override_cloud_dispatch(self, monkeypatch, tmp_path):
        settings = SettingsStore(tmp_path / "settings.json")
        settings.set("privacy_mode", "cloud_allowed")
        monkeypatch.setattr("core.settings.get_settings", lambda: settings)

        # Mock custom provider
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "CustomMock"
        mock_provider.key = "custom"
        mock_provider.is_ready.return_value = True
        mock_provider.list_models.return_value = [
            ModelInfo(id="custom-fast", name="Custom Fast", provider="custom", speed_tier=SpeedTier.FAST)
        ]
        mock_provider.chat.return_value = ChatResponse(
            text="Mock cloud answer",
            model_id="custom-fast",
            provider="custom",
        )

        reg = ProviderRegistry()
        reg.register(mock_provider)
        monkeypatch.setattr("core.providers.registry.get_registry", lambda: reg)

        orch = Orchestrator()
        res = orch.submit("general non-agent query", options=TurnOptions(model_override="custom/custom-fast"))
        assert res.text == "Mock cloud answer"
        assert res.model_used == "custom-fast"
        assert "model_override:custom/custom-fast" in res.routing_reason
        mock_provider.chat.assert_called_once()

    def test_turn_options_forced_tier_routing(self, monkeypatch, tmp_path):
        settings = SettingsStore(tmp_path / "settings.json")
        settings.set("privacy_mode", "cloud_allowed")
        monkeypatch.setattr("core.settings.get_settings", lambda: settings)

        mock_fast_provider = MagicMock(spec=LLMProvider)
        mock_fast_provider.name = "FastCloud"
        mock_fast_provider.key = "fastcloud"
        mock_fast_provider.is_ready.return_value = True
        mock_fast_provider.list_models.return_value = [
            ModelInfo(id="fast-1", name="Fast 1", provider="fastcloud", speed_tier=SpeedTier.FAST)
        ]
        mock_fast_provider.chat.return_value = ChatResponse(
            text="Fast response",
            model_id="fast-1",
            provider="fastcloud",
        )

        reg = ProviderRegistry()
        reg.register(mock_fast_provider)
        monkeypatch.setattr("core.providers.registry.get_registry", lambda: reg)

        orch = Orchestrator()
        res = orch.submit("non-agent query", options=TurnOptions(forced_tier="fast"))
        assert res.text == "Fast response"
        assert res.model_used == "fast-1"
        assert "forced_tier:fast:fastcloud/fast-1" in res.routing_reason


class TestPostBatchBCohesionAndRegression:
    """Cohesion and regression tests for ChatOptions.model, LocalLLMProvider, default registry, and Orchestrator."""

    def test_chat_options_model_propagation_to_providers(self, monkeypatch):
        mock_settings = MagicMock()
        mock_settings.get.return_value = "cloud_allowed"
        monkeypatch.setattr("core.settings.get_settings", lambda: mock_settings)

        # 1. Anthropic Provider
        anthropic = AnthropicProvider(api_key="sk-ant-test")
        mock_resp_ant = MagicMock()
        mock_resp_ant.status_code = 200
        mock_resp_ant.json.return_value = {
            "content": [{"type": "text", "text": "Anthropic custom model answer"}],
            "model": "claude-custom-123",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        with patch("httpx.post", return_value=mock_resp_ant) as mock_post:
            resp = anthropic.chat(
                [ChatMessage(role="user", content="hello")],
                options=ChatOptions(model="claude-custom-123"),
            )
            assert resp.text == "Anthropic custom model answer"
            called_payload = mock_post.call_args[1]["json"]
            assert called_payload["model"] == "claude-custom-123"

        # 2. OpenAI Compatible Provider
        openai = OpenAICompatibleProvider(name="OpenAI", key="openai", base_url="https://api.openai.com/v1", api_key="sk-test")
        mock_resp_oa = MagicMock()
        mock_resp_oa.status_code = 200
        mock_resp_oa.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "OpenAI custom model answer"}}],
            "model": "gpt-custom-99",
            "usage": {"total_tokens": 15},
        }

        with patch("httpx.post", return_value=mock_resp_oa) as mock_post:
            resp_oa = openai.chat(
                [ChatMessage(role="user", content="hello")],
                options=ChatOptions(model="gpt-custom-99"),
            )
            assert resp_oa.text == "OpenAI custom model answer"
            called_payload_oa = mock_post.call_args[1]["json"]
            assert called_payload_oa["model"] == "gpt-custom-99"

        # 3. Google Provider
        google = GoogleProvider(api_key="goog-test")
        mock_resp_g = MagicMock()
        mock_resp_g.status_code = 200
        mock_resp_g.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "Google custom model answer"}]},
                "finishReason": "STOP",
            }],
            "usageMetadata": {"totalTokenCount": 25},
        }

        with patch("httpx.post", return_value=mock_resp_g) as mock_post:
            resp_g = google.chat(
                [ChatMessage(role="user", content="hello")],
                options=ChatOptions(model="gemini-custom-flash"),
            )
            assert resp_g.text == "Google custom model answer"
            called_url = mock_post.call_args[0][0]
            assert "gemini-custom-flash:generateContent" in called_url

    def test_local_llm_provider_adapter(self, monkeypatch):
        from core.providers.local import LocalLLMProvider, LocalProvider

        local_prov = LocalLLMProvider()
        assert isinstance(local_prov, LLMProvider)
        assert local_prov.key == "local"
        assert local_prov.is_local is True
        assert local_prov.is_authenticated is True
        assert local_prov.is_reachable is True

        monkeypatch.setattr(LocalProvider, "is_available", classmethod(lambda cls: True))
        assert local_prov.is_ready() is True
        val_ok, msg = local_prov.validate_key()
        assert val_ok is True
        assert msg == "OK"

        models = local_prov.list_models()
        assert len(models) == 1
        assert models[0].id == "local"
        assert models[0].catalog_source == CatalogSource.LIVE
        assert models[0].speed_tier == SpeedTier.SLOW

        monkeypatch.setattr(LocalProvider, "chat", classmethod(lambda cls, msgs, **kwargs: "Mock Local Output"))
        chat_resp = local_prov.chat([ChatMessage(role="user", content="Hi")])
        assert chat_resp.text == "Mock Local Output"
        assert chat_resp.model_id == "local"
        assert chat_resp.provider == "local"

        def mock_stream(cls, msgs, **kwargs):
            yield "token1 "
            yield "token2"
        monkeypatch.setattr(LocalProvider, "chat_stream", classmethod(mock_stream))
        streamed = list(local_prov.stream([ChatMessage(role="user", content="Hi")]))
        assert streamed == ["token1 ", "token2"]

    def test_get_registry_default_providers_and_bridge_integration(self, monkeypatch, tmp_path):
        import json
        from app.bridge import Bridge
        from core.providers.registry import get_registry
        from core.security.secrets import SecretsVault

        vault = SecretsVault(tmp_path / "secrets.enc")
        monkeypatch.setattr("core.security.secrets.get_vault", lambda: vault)
        reg = get_registry()

        # Pre-registered providers exist
        assert reg.get("local") is not None
        assert reg.get("google") is not None
        assert reg.get("anthropic") is not None
        assert reg.get("openai") is not None

        bridge = Bridge()
        providers_json = bridge.get_providers()
        providers_data = json.loads(providers_json)
        local_entry = next(p for p in providers_data if p["key"] == "local")
        assert local_entry["has_key"] is True  # local doesn't require an API key

        google_entry = next(p for p in providers_data if p["key"] == "google")
        assert google_entry["has_key"] is False

        # Save key via bridge and verify registered instance is updated
        bridge.save_provider_key("google", "test-new-google-key")
        assert vault.retrieve_key("google") == "test-new-google-key"
        reg_google = reg.get("google")
        assert getattr(reg_google, "_api_key") == "test-new-google-key"

    def test_orchestrator_system_prompt_and_agent_context_model_override(self, monkeypatch, tmp_path):
        from core.providers.local import LocalProvider

        settings = SettingsStore(tmp_path / "settings.json")
        settings.set("system_prompt", "Custom Educator Prompt for testing.")
        settings.set("router_preference", "local_only")
        monkeypatch.setattr("core.settings.get_settings", lambda: settings)

        # 1. Router preference local_only forces LOCAL_ONLY execution mode
        captured_messages = []
        def mock_local_chat(messages, **kwargs):
            captured_messages.extend(messages)
            return "Local reply"
        monkeypatch.setattr(LocalProvider, "chat", mock_local_chat)

        orch = Orchestrator()
        res = orch.submit("Random query without agent match")
        assert res.execution_mode == "local_only"
        assert res.text == "Local reply"
        # Verify custom system prompt was passed
        sys_msgs = [m for m in captured_messages if m.get("role") == "system"]
        assert len(sys_msgs) > 0
        assert sys_msgs[0]["content"] == "Custom Educator Prompt for testing."

        # 2. Verify model_override in AgentContext
        from core.agents.registry import AgentResponse, agent_registry

        @agent_registry.register(
            name="TestContextAgent",
            triggers=["inspect context"],
        )
        class TestContextAgent:
            def process(self, context):
                return AgentResponse(text=f"Override: {context.model_override}", agent_name="TestContextAgent")

        res_agent = orch.submit(
            "inspect context please",
            options=TurnOptions(model_override="local"),
        )
        assert "Override: local" in res_agent.text
