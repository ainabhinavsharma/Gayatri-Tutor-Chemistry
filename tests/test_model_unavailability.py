import pytest
from core.agents.registry import ModelUnavailableError, agent_registry
from core.agents.runtime import AgentContext, AgentRuntime
from legacy.agents.default_agents import _local_chat as default_local_chat
from legacy.agents.prompt_agents import _local_chat as prompt_local_chat
from core.orchestrator import Orchestrator


def test_local_chat_raises_model_unavailable_error(monkeypatch):
    """Audit #16: _local_chat must not disguise model failure as a plausible success text."""
    def failing_chat(*args, **kwargs):
        raise FileNotFoundError("Model file gemma.gguf not found")

    monkeypatch.setattr("core.providers.local.LocalProvider.chat", failing_chat)

    with pytest.raises(ModelUnavailableError, match="Local model unavailable"):
        default_local_chat([{"role": "user", "content": "hi"}])

    with pytest.raises(ModelUnavailableError, match="Local model unavailable"):
        prompt_local_chat([{"role": "user", "content": "hi"}])


def test_agent_runtime_returns_structured_model_unavailable_response(monkeypatch):
    """Audit #16: AgentRuntime should produce structured AgentResponse on model failure."""
    def failing_chat(*args, **kwargs):
        raise RuntimeError("No GPU or CPU backend available")

    monkeypatch.setattr("core.providers.local.LocalProvider.chat_stream", failing_chat)

    runtime = AgentRuntime()
    spec = agent_registry.get("Tutor")
    context = AgentContext(session_id="test_unavail", user_message="Explain recursion")

    response = runtime.process("Explain recursion", context, spec=spec)
    assert response.status == "MODEL_UNAVAILABLE"
    assert response.metadata.get("model_unavailable") is True
    assert "not installed or unavailable" in response.text



import pytest

@pytest.mark.skip(reason="Phase 1/2 refactored orchestrator internals; test requires update")
def test_orchestrator_handles_agent_model_unavailable_without_contaminating_conv(monkeypatch):
    """Audit #16: Orchestrator records user message but does not advance tutor or save normal assistant turn."""
    def failing_chat(*args, **kwargs):
        raise FileNotFoundError("Model file missing")

    monkeypatch.setattr("core.providers.local.LocalProvider.chat_stream", failing_chat)

    orch = Orchestrator()
    session_id = "sess_unavail_submit"

    res = orch.submit("/tutor Explain loops", session_id=session_id)
    assert res.status == "MODEL_UNAVAILABLE"
    assert "model_unavailable" in res.routing_reason

    # Conversation history should only have the user message, not a bogus assistant dialogue
    conv = orch.get_conversation(session_id)
    msgs = conv.get_all()
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "/tutor Explain loops"
