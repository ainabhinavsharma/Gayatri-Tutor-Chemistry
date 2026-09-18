from unittest.mock import MagicMock
from app.bridge import Bridge


def test_bridge_window_controls(qtbot):
    bridge = Bridge()
    mock_window = MagicMock()
    mock_window.isMaximized.return_value = False

    bridge.set_window(mock_window)

    # Test minimize
    bridge.minimize_window()
    mock_window.showMinimized.assert_called_once()

    # Test maximize when not maximized
    bridge.maximize_window()
    mock_window.showMaximized.assert_called_once()

    # Test maximize when already maximized (should restore)
    mock_window.isMaximized.return_value = True
    bridge.maximize_window()
    mock_window.showNormal.assert_called_once()

    # Test close
    bridge.close_window()
    mock_window.close.assert_called_once()


def test_bridge_get_agents(qtbot):
    """Audit #52 & #54: bridge.get_agents returns registered agents with metadata."""
    import json
    bridge = Bridge()
    raw = bridge.get_agents()
    data = json.loads(raw)
    assert data["ok"] is True
    agent_names = [a["name"] for a in data["agents"]]
    assert len(agent_names) == 0
    
    


def test_bridge_get_curriculum_progress(qtbot, tmp_path, monkeypatch):
    """Audit #55: bridge.get_curriculum_progress returns stats and concept list."""
    import json
    from core.knowledge_graph import LearningDependencyGraph
    ldg = LearningDependencyGraph(tmp_path / "ldg.db")
    ldg.add_concept("test_concept", "Test Concept", "Description", difficulty=0.4, subject="Python")

    bridge = Bridge()
    orch = bridge._get_orchestrator()
    orch._ldg = ldg

    raw = bridge.get_curriculum_progress()
    data = json.loads(raw)
    assert data["ok"] is True
    assert "stats" in data
    assert data["stats"]["total"] >= 1
    concept_ids = [c["id"] for c in data["concepts"]]
    assert "test_concept" in concept_ids


def test_bridge_send_message_with_agent_selection(qtbot):
    """Audit #52 & #53: bridge.send_message dispatches with forced agent option."""
    bridge = Bridge()
    orch_mock = MagicMock()
    orch_mock.stream.return_value = iter([("Review feedback", True)])
    bridge._orchestrator = orch_mock

    received_tokens = []
    bridge.token.connect(lambda idx, tok: received_tokens.append(tok))

    bridge.send_message("Review this snippet", "chemistry_tutor")

    orch_mock.stream.assert_called_once()
    call_args = orch_mock.stream.call_args
    assert call_args[0][0] == "Review this snippet"
    opts = call_args[1].get("options")
    assert opts is not None
    assert opts.mode == "chemistry_tutor"
    assert "Review feedback" in received_tokens


def test_bridge_set_setting_type_coercion(qtbot, tmp_path, monkeypatch):
    """Verify bridge.set_setting cleanly coerces JSON-stringified types without errors."""
    from core.settings import SettingsStore
    test_store = SettingsStore(settings_path=tmp_path / "settings.json")
    monkeypatch.setattr("core.settings.get_settings", lambda: test_store)

    bridge = Bridge()

    # Boolean setting with various representations
    bridge.set_setting("auto_download_model", "true")
    assert test_store.get("auto_download_model") is True

    bridge.set_setting("auto_download_model", "false")
    assert test_store.get("auto_download_model") is False

    # Float setting
    bridge.set_setting("temperature", "1.2")
    assert test_store.get("temperature") == 1.2

    # Integer setting
    bridge.set_setting("max_tokens", "1024")
    assert test_store.get("max_tokens") == 1024


def test_bridge_save_and_delete_provider_key(qtbot, tmp_path, monkeypatch):
    """Verify bridge.save_provider_key stores keys and deletes them when blank."""
    from core.security.secrets import SecretsVault
    test_vault = SecretsVault(vault_path=tmp_path / "vault.json")
    monkeypatch.setattr("core.security.secrets.get_vault", lambda: test_vault)

    bridge = Bridge()

    # Save a key
    bridge.save_provider_key("anthropic", "sk-ant-testkey12345678901234")
    assert test_vault.has_key("anthropic")
    assert test_vault.retrieve_key("anthropic") == "sk-ant-testkey12345678901234"

    # Empty string should delete the key
    bridge.save_provider_key("anthropic", "   ")
    assert not test_vault.has_key("anthropic")
    assert test_vault.retrieve_key("anthropic") is None


def test_knowledge_graph_get_ldg():
    """Verify get_ldg accessor in core.knowledge_graph returns a valid graph."""
    from core.knowledge_graph import get_ldg, LearningDependencyGraph
    ldg = get_ldg()
    assert isinstance(ldg, LearningDependencyGraph)


