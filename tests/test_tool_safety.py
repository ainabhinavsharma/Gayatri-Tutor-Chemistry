import pytest
from core.agents.runtime import ToolRegistry, AgentRuntime, AgentContext
from core.agents.registry import AgentResponse, AgentSpec


def test_tool_registry_duplicate_registration_rejected():
    """Audit #13: Duplicate registrations must be rejected unless allow_replace=True."""
    registry = ToolRegistry()

    @registry.register(name="calculator")
    def calc_v1(x: int) -> int:
        return x * 2

    # Duplicate registration without allow_replace should raise ValueError
    with pytest.raises(ValueError, match="already registered"):
        @registry.register(name="calculator")
        def calc_v2(x: int) -> int:
            return x * 3

    # With allow_replace=True, override is allowed
    @registry.register(name="calculator", allow_replace=True)
    def calc_v3(x: int) -> int:
        return x * 4

    assert registry.call("calculator", x=5) == 20


def test_tool_argument_schema_validation():
    """Audit #12: Tool arguments should be validated against argument_schema."""
    registry = ToolRegistry()

    @registry.register(name="multiply", argument_schema={"a": int, "b": int})
    def multiply(a: int, b: int) -> int:
        return a * b

    # Valid arguments
    assert registry.call("multiply", a=3, b=4) == 12

    # Invalid type
    with pytest.raises(TypeError, match="must be of type int"):
        registry.call("multiply", a="not_an_int", b=4)


def test_agent_runtime_handles_unknown_tool_gracefully():
    """Audit #12: Unknown tool requests from model are caught and sanitized."""
    registry = ToolRegistry()
    runtime = AgentRuntime(tools=registry)

    class DummyToolAgent:
        def __init__(self):
            self.step = 0

        def process(self, context):
            self.step += 1
            if self.step == 1:
                return AgentResponse(
                    text="Calling unknown tool",
                    agent_name="Dummy",
                    tool_calls=[{"tool": "non_existent_tool", "args": {"foo": "bar"}}],
                )
            # Second step: inspection of feedback
            results = context.metadata.get("tool_results", [])
            assert len(results) == 1
            assert "not recognized" in results[0]["error"]
            return AgentResponse(text="Handled gracefully", agent_name="Dummy")

    spec = AgentSpec(name="Dummy")
    context = AgentContext(session_id="test_tool", user_message="do work")
    res = runtime._agent_loop(DummyToolAgent(), spec, context)
    assert res.text == "Handled gracefully"


def test_agent_runtime_sanitizes_tool_error():
    """Audit #12: Tool errors fed back to model are sanitized to avoid leaking internals."""
    registry = ToolRegistry()

    @registry.register(name="failing_tool")
    def fail(path: str):
        raise FileNotFoundError(f"Sensitive internal path /etc/secret/keys.json not found: {path}")

    runtime = AgentRuntime(tools=registry)

    class FailingAgent:
        def __init__(self):
            self.step = 0

        def process(self, context):
            self.step += 1
            if self.step == 1:
                return AgentResponse(
                    text="Calling failing tool",
                    agent_name="Failing",
                    tool_calls=[{"tool": "failing_tool", "args": {"path": "test"}}],
                )
            results = context.metadata.get("tool_results", [])
            assert len(results) == 1
            error_msg = results[0]["error"]
            # Must NOT leak the raw internal path into model-facing error
            assert "/etc/secret/keys.json" not in error_msg
            assert "Tool execution failed" in error_msg
            return AgentResponse(text="Error recovered", agent_name="Failing")

    spec = AgentSpec(name="Failing")
    context = AgentContext(session_id="test_tool_err", user_message="run fail")
    res = runtime._agent_loop(FailingAgent(), spec, context)
    assert res.text == "Error recovered"


def test_tool_execution_timeout():
    """Audit #79: Tool execution timeout is enforced by ToolRegistry."""
    import time
    registry = ToolRegistry()

    @registry.register(name="slow_tool", timeout_s=0.2)
    def slow():
        time.sleep(1.0)
        return "finished"

    with pytest.raises(TimeoutError, match="timed out"):
        registry.call("slow_tool")


def test_tool_path_traversal_blocked():
    """Audit #80: Path traversal in tool arguments is rejected."""
    from core.agents.runtime import ToolRegistry, FileToolInput
    registry = ToolRegistry()

    class ReadFileModel(FileToolInput):
        file_path: str

    @registry.register(name="read_file", input_model=ReadFileModel)
    def read_file(file_path: str):
        return f"read {file_path}"

    with pytest.raises(TypeError, match="Path traversal detected"):
        registry.call("read_file", file_path="../../etc/passwd")

    with pytest.raises(TypeError, match="Path traversal detected"):
        registry.call("read_file", file_path="C:\\safe\\..\\secret.txt")

    with pytest.raises(TypeError, match="Path traversal detected"):
        registry.call("read_file", file_path="C:\\Windows\\System32\\config\\SAM")

    # Safe path succeeds
    assert registry.call("read_file", file_path="safe_doc.txt") == "read safe_doc.txt"


def test_orchestrator_forced_agent_dispatch():
    """Audit #52: Forced agent dispatch honors options.forced_agent."""
    from core.orchestrator import Orchestrator, TurnOptions
    from core.agents.default_agents import register_default_agents
    register_default_agents()

    orch = Orchestrator()
    opts = TurnOptions(forced_agent="Code Reviewer")
    spec, conf, reason, _ = orch._resolve_agent("tell me a joke", opts)
    assert spec is not None
    assert spec.name == "Code Reviewer"
    assert "forced_agent:Code Reviewer" in reason


def test_orchestrator_forced_tier_local_only():
    """Audit #91: In LOCAL_ONLY mode, forced_tier routes to local provider."""
    from core.orchestrator import Orchestrator, TurnOptions
    from core.config import ExecutionMode
    from core.providers.local import LocalProvider

    orch = Orchestrator()
    opts = TurnOptions(forced_tier="fast")
    prov, model_id, reason = orch._resolve_provider(opts, exec_mode=ExecutionMode.LOCAL_ONLY)
    assert prov is LocalProvider
    assert model_id == "local"
    assert "forced_tier_local_only" in reason

