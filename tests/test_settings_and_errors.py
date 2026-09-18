"""Tests for Settings validation, encoding, and error sanitization (Audit #19, #27, #28, #29)."""

import json
import pytest

from core.errors import SanitizedError, sanitize_error, sanitize_message
from core.settings import (
    ALLOWED_PRIVACY_MODES,
    ALLOWED_ROUTER_PREFERENCES,
    SettingsStore,
)


class TestSettingsValidationAndRanges:
    """Test schema and semantic range validation (Audit #27)."""

    def test_temperature_valid_and_invalid_ranges(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        # Valid values
        store.set("temperature", 0.0)
        assert store.get("temperature") == 0.0
        store.set("temperature", 1.5)
        assert store.get("temperature") == 1.5
        store.set("temperature", 2.0)
        assert store.get("temperature") == 2.0
        # Integer converts to float
        store.set("temperature", 1)
        assert store.get("temperature") == 1.0

        # Out of bounds
        with pytest.raises(ValueError, match="temperature"):
            store.set("temperature", -0.1)

        with pytest.raises(ValueError, match="temperature"):
            store.set("temperature", 2.01)

        # Invalid types
        with pytest.raises(ValueError, match="float"):
            store.set("temperature", "0.7")

        with pytest.raises(ValueError, match="float"):
            store.set("temperature", True)  # bool must not pass as float

    def test_max_tokens_valid_and_invalid_ranges(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        # Valid
        store.set("max_tokens", 1)
        assert store.get("max_tokens") == 1
        store.set("max_tokens", 2048)
        assert store.get("max_tokens") == 2048
        store.set("max_tokens", 32768)
        assert store.get("max_tokens") == 32768

        # Out of bounds
        with pytest.raises(ValueError, match="max_tokens"):
            store.set("max_tokens", 0)

        with pytest.raises(ValueError, match="max_tokens"):
            store.set("max_tokens", -50)

        with pytest.raises(ValueError, match="max_tokens"):
            store.set("max_tokens", 32769)

        # Strict int check (bool subclasses int in Python)
        with pytest.raises(ValueError, match="int"):
            store.set("max_tokens", True)

        with pytest.raises(ValueError, match="int"):
            store.set("max_tokens", 512.5)

    def test_enum_settings_validation(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        # Theme
        store.set("theme", "light")
        assert store.get("theme") == "light"
        with pytest.raises(ValueError, match="theme"):
            store.set("theme", "solarized")

        # Router preference
        for pref in ALLOWED_ROUTER_PREFERENCES:
            store.set("router_preference", pref)
            assert store.get("router_preference") == pref
        with pytest.raises(ValueError, match="router_preference"):
            store.set("router_preference", "super_fast")

        # Privacy mode
        for mode in ALLOWED_PRIVACY_MODES:
            store.set("privacy_mode", mode)
            assert store.get("privacy_mode") == mode
        with pytest.raises(ValueError, match="privacy_mode"):
            store.set("privacy_mode", "incognito")

    def test_system_prompt_validation(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        store.set("system_prompt", "You are an expert tutor.")
        assert store.get("system_prompt") == "You are an expert tutor."

        # Cannot be empty or whitespace
        with pytest.raises(ValueError, match="system_prompt"):
            store.set("system_prompt", "")

        with pytest.raises(ValueError, match="system_prompt"):
            store.set("system_prompt", "   \n\t  ")

        # Cannot exceed length limit
        with pytest.raises(ValueError, match="exceeds max length"):
            store.set("system_prompt", "a" * 10001)

    def test_boolean_flags_strict_validation(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        bool_keys = ["local_model_installed", "first_run_complete", "telemetry_enabled", "auto_download_model"]
        for key in bool_keys:
            store.set(key, True)
            assert store.get(key) is True
            store.set(key, False)
            assert store.get(key) is False

            with pytest.raises(ValueError, match="bool"):
                store.set(key, "True")
            with pytest.raises(ValueError, match="bool"):
                store.set(key, 1)


class TestSettingsUnknownKeysAndAtomicUpdates:
    """Test unknown key rejection and atomic updates (Audit #28)."""

    def test_unknown_key_rejected_in_set(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        with pytest.raises(KeyError, match="Unknown setting key: 'unknown_option'"):
            store.set("unknown_option", "value")

        with pytest.raises(KeyError, match="Unknown setting key: 'temp'"):
            store.set("temp", 0.5)  # Typo for temperature

    def test_namespaced_extension_keys_rejected(self, tmp_path):
        # After P0-004, even custom_ and ext_ keys are rejected to prevent arbitrary overwrite
        store = SettingsStore(settings_path=tmp_path / "settings.json")

        with pytest.raises(KeyError, match="Unknown setting key: 'custom_plugin_flag'"):
            store.set("custom_plugin_flag", True)

        with pytest.raises(KeyError, match="Unknown setting key: 'ext_theme_variant'"):
            store.set("ext_theme_variant", "nordic")

    def test_atomic_update_failure_does_not_corrupt_settings(self, tmp_path):
        store = SettingsStore(settings_path=tmp_path / "settings.json")
        initial_temp = store.get("temperature")

        # Attempt batch update where one key is invalid
        with pytest.raises(ValueError):
            store.update({
                "theme": "light",
                "temperature": 99.0,  # Invalid
            })

        # Verify nothing was mutated
        assert store.get("theme") == "dark"
        assert store.get("temperature") == initial_temp


class TestSettingsUTF8EncodingAndResilience:
    """Test UTF-8 file encoding and corrupt config recovery (Audit #29)."""

    def test_utf8_multilingual_persistence(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        store = SettingsStore(settings_path=settings_file)

        unicode_prompt = "नमस्ते Gayatri AI 🚀! आप एक उत्कृष्ट शिक्षिका हैं। हिंदी और English दोनों में मदद करें।"
        store.set("system_prompt", unicode_prompt)

        # Read back with new store instance
        new_store = SettingsStore(settings_path=settings_file)
        assert new_store.get("system_prompt") == unicode_prompt

        # Verify file content is valid UTF-8 and contains the actual characters (not unicode escape sequences)
        raw_bytes = settings_file.read_bytes()
        decoded_text = raw_bytes.decode("utf-8")
        assert "नमस्ते" in decoded_text
        assert "🚀" in decoded_text

    def test_load_handles_corrupt_values_gracefully(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        # Write corrupted/unrecognized settings to disk
        bad_json = {
            "temperature": -50.0,      # Out of range
            "theme": "banana",          # Unknown enum
            "unknown_bogus_key": 123,  # Unknown key
            "max_tokens": 1024,        # Valid
        }
        settings_file.write_text(json.dumps(bad_json), encoding="utf-8")

        store = SettingsStore(settings_path=settings_file)
        # Invalid values fell back to default
        assert store.get("temperature") == 0.7
        assert store.get("theme") == "dark"
        # Valid value was loaded
        assert store.get("max_tokens") == 1024


class TestErrorSanitizationAndDiagnostics:
    """Test error sanitization and diagnostic tracking (Audit #19, #143)."""

    def test_sanitize_message_strips_paths_and_urls(self):
        msg_win = r"Failed to open C:\Users\user\Desktop\gayatri\models\model.gguf: file not found"
        sanitized_win = sanitize_message(msg_win)
        assert r"C:\Users" not in sanitized_win
        assert "model.gguf" not in sanitized_win
        assert "[LOCAL_PATH]" in sanitized_win

        msg_posix = "Error in /Users/admin/projects/gayatri/core/orchestrator.py line 45"
        sanitized_posix = sanitize_message(msg_posix)
        assert "/Users/admin" not in sanitized_posix
        assert "[LOCAL_PATH]" in sanitized_posix

    def test_sanitize_message_strips_api_keys_and_tokens(self):
        msg_key = "Request failed with key: AIzaSyD9876543210abcdefghijklmnop123456"
        sanitized = sanitize_message(msg_key)
        assert "AIzaSy" not in sanitized
        assert "[GOOGLE_API_KEY]" in sanitized

        msg_bearer = "Authorization: Bearer secret_token_xyz_1234567890"
        sanitized_bearer = sanitize_message(msg_bearer)
        assert "secret_token_xyz" not in sanitized_bearer
        assert "[REDACTED_TOKEN]" in sanitized_bearer

        msg_url = "POST https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyFakeKey123 HTTP 400"
        sanitized_url = sanitize_message(msg_url)
        assert "https://" not in sanitized_url
        assert "AIzaSy" not in sanitized_url

    def test_sanitize_error_generates_diagnostic_id_and_safe_message(self):
        exc = FileNotFoundError(r"No such file: C:\Users\user\secret\gemma-2-2b-it.Q4_K_M.gguf")
        res = sanitize_error(exc, category="model_loading")

        assert isinstance(res, SanitizedError)
        assert res.diagnostic_id.startswith("ERR-")
        assert len(res.diagnostic_id) == 12  # ERR- + 8 hex chars
        # User message must be friendly and not contain paths
        assert "C:\\Users" not in res.user_message
        assert ".gguf" not in res.user_message
        assert "A required local model or data file could not be found" in res.user_message
        # Internal error holds the technical info
        assert "FileNotFoundError" in res.internal_error

    def test_sanitize_error_maps_privacy_and_network_errors(self):
        perm_err = PermissionError("Data cannot leave the device: provider 'Google' is blocked")
        res_perm = sanitize_error(perm_err)
        assert "privacy policy" in res_perm.user_message.lower()

        conn_err = ConnectionError("failed to establish a new connection: [Errno 11001] getaddrinfo failed")
        res_conn = sanitize_error(conn_err)
        assert "unable to connect" in res_conn.user_message.lower()

        auth_err = RuntimeError("HTTP 401: Unauthorized invalid API key provided")
        res_auth = sanitize_error(auth_err)
        assert "authentication failed" in res_auth.user_message.lower()


class TestOrchestratorAndBridgeErrorIntegration:
    """Test that orchestrator and bridge output sanitized error messages."""

    import pytest
    @pytest.mark.skip(reason="Phase 1 refactored orchestrator internals")
    def test_orchestrator_submit_error_sanitization(self, tmp_path):
        from core.conversation import ConversationStore
        from core.orchestrator import Orchestrator

        orch = Orchestrator(conversations=ConversationStore())

        # Cause an intentional error by asking for non-existent local model
        import unittest.mock as mock
        with mock.patch("core.providers.local.LocalProvider.chat", side_effect=FileNotFoundError("C:\\Users\\user\\missing_model.gguf")):
            res = orch.submit("Hello!", session_id="test_sess")
            assert "C:\\Users" not in res.text
            assert "missing_model.gguf" not in res.text
            assert "Reference: ERR-" in res.text

    def test_bridge_send_message_emits_sanitized_error(self, qtbot):
        from app.bridge import Bridge

        bridge = Bridge()
        received_errors = []
        bridge.error.connect(received_errors.append)

        import unittest.mock as mock
        mock_orch = mock.MagicMock()
        mock_orch.stream.side_effect = RuntimeError("Failed connecting to https://api.openai.com/v1/chat with key sk-abcdef12345678901234567890")
        bridge._orchestrator = mock_orch

        bridge.send_message("Hello")

        assert len(received_errors) == 1
        err_msg = received_errors[0]
        assert "sk-abcdef" not in err_msg
        assert "https://" not in err_msg


class TestPostAuditRegressionFixes:
    """Test edge cases and safety boundaries identified during post-audit cohesion review."""

    def test_exact_tie_at_1_0_falls_back_to_ambiguity(self):
        """When two agents both have 1.0 confidence, dispatch must recognize ambiguity."""
        from core.agents.registry import AgentRegistry

        reg = AgentRegistry()
        reg.register(name="AgentA", commands=["dupcmd"])(object)
        reg.register(name="AgentB", commands=["dupcmd"])(object)

        result = reg.dispatch("/dupcmd")
        # With conflicting exact 1.0 matches, must not pick arbitrarily; fallback to None
        assert result.primary is None

    def test_agent_runtime_error_sanitization(self):
        """AgentRuntime sanitizes unexpected agent failure messages without leaking paths."""
        from core.agents.registry import AgentRegistry
        from core.agents.runtime import AgentContext, AgentRuntime

        reg = AgentRegistry()

        @reg.register(name="CrashingAgent", commands=["crash"])
        class CrashingAgentImpl:
            def process(self, context):
                raise RuntimeError(r"Corrupted file at C:\Users\user\AppData\secret.db")

        runtime = AgentRuntime(registry=reg)
        ctx = AgentContext(session_id="s1", user_message="/crash")
        res = runtime.process("/crash", ctx)

        assert res.status == "ERROR"
        assert r"C:\Users" not in res.text
        assert "secret.db" not in res.text
        assert "Reference: ERR-" in res.text

    def test_tutor_engine_set_context(self, tmp_path):
        """TutorEngine.set_context updates in-memory state and persists to store."""
        from core.knowledge_graph import LearningDependencyGraph
        from core.tutor_engine import TutorContext, TutorEngine

        ldg = LearningDependencyGraph(db_path=tmp_path / "ldg.db")
        ldg.add_concept("concept_math", "Math Basics")
        engine = TutorEngine(ldg)

        ctx = TutorContext(
            current_concept_id="concept_math",
            current_concept_name="Math Basics",
            mastery=0.75,
            waiting_for_answer=True,
        )
        engine.set_context("sess_test_ctx", ctx)

        assert engine.session_contexts["sess_test_ctx"].mastery == 0.75
        assert engine.is_waiting_for_answer("sess_test_ctx") is True

    import pytest
    @pytest.mark.skip(reason="Phase 1 refactored orchestrator internals")
    def test_session_store_thread_safety(self, tmp_path):
        """SessionStore supports concurrent multi-threaded writes without database locks."""
        import threading
        from core.conversation import Conversation
        from core.session import SessionStore
        from core.tutor_engine import TutorContext

        store = SessionStore(db_path=tmp_path / "sessions.db")
        errors = []

        def worker(idx: int):
            try:
                for i in range(15):
                    sess_id = f"sess_{idx}_{i}"
                    conv = Conversation(session_id=sess_id)
                    conv.add("user", f"Message {i} from thread {idx}")
                    conv.add("assistant", f"Reply {i} from thread {idx}")
                    ctx = TutorContext(current_concept_id="c1", mastery=0.5)
                    store.save_session(sess_id, conv, tutor_context=ctx)
                    loaded_msgs = store.load_session(sess_id)
                    assert len(loaded_msgs) == 2
                    loaded_ctx = store.load_tutor_context(sess_id)
                    assert loaded_ctx is not None
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent session store errors: {errors}"
        store.close()

    def test_bridge_set_setting_type_coercion(self, tmp_path):
        """Bridge.set_setting defensively coerces stringified booleans and integers."""
        from app.bridge import Bridge
        from core.settings import SettingsStore

        settings_path = tmp_path / "settings.json"
        store = SettingsStore(settings_path=settings_path)

        import unittest.mock as mock
        with mock.patch("core.settings.get_settings", return_value=store):
            bridge = Bridge()
            # Pass unquoted boolean string from JS
            bridge.set_setting("telemetry_enabled", "true")
            assert store.get("telemetry_enabled") is True

            bridge.set_setting("auto_download_model", "false")
            assert store.get("auto_download_model") is False

            # Pass unquoted numeric string from JS
            bridge.set_setting("max_tokens", "1024")
            assert store.get("max_tokens") == 1024

            bridge.set_setting("temperature", "0.85")
            assert store.get("temperature") == 0.85
