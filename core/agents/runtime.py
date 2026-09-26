"""Gayatri AI — Agent runtime: context, tool dispatch, agent loop."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.agents.registry import AgentResponse, AgentSpec, ModelUnavailableError, agent_registry

logger = logging.getLogger("gayatri.agents.runtime")


@dataclass
class AgentContext:
    """Context passed to agents during processing."""
    session_id: str
    user_message: str
    history: list[dict] = field(default_factory=list)
    model_tier: str = "local"
    model_override: str | None = None
    metadata: dict = field(default_factory=dict)


from pydantic import BaseModel, ValidationError, field_validator

from core.config import TOOL_ARG_MAX_STRING_LENGTH


@dataclass
class ToolSpec:
    """Specification of a tool registered with ToolRegistry."""
    name: str
    func: Callable
    description: str = ""
    argument_schema: dict[str, type] | None = None
    input_model: type[BaseModel] | None = None
    timeout_s: float = 30.0
    cancellation_token: bool = False  # Not actually used in spec directly


def safe_log_args(kwargs: dict) -> dict:
    """Redact sensitive arguments for logging (PRIV-002)."""
    sensitive_keys = {'key', 'token', 'secret', 'password', 'content', 'answer', 'message'}
    safe_kwargs = {}
    for k, v in kwargs.items():
        if any(sensitive in k.lower() for sensitive in sensitive_keys):
            safe_kwargs[k] = "[REDACTED]"
        else:
            safe_kwargs[k] = v
    return safe_kwargs


class ToolRegistry:
    """Registry of available tools that agents can call."""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str = "",
        argument_schema: dict[str, type] | None = None,
        input_model: type[BaseModel] | None = None,
        timeout_s: float = 30.0,
        allow_replace: bool = False,
    ) -> Callable:
        """Decorator to register a tool function. Rejects duplicate registrations unless allow_replace=True."""
        def decorator(func: Callable) -> Callable:
            if name in self._tools and not allow_replace:
                raise ValueError(
                    f"Tool '{name}' is already registered. Set allow_replace=True to explicitly overwrite."
                )
            self._tools[name] = ToolSpec(
                name=name,
                func=func,
                description=description,
                argument_schema=argument_schema,
                input_model=input_model,
                timeout_s=timeout_s,
            )
            logger.info(f"Registered tool: {name}")
            return func
        return decorator

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def call(self, name: str, **kwargs) -> Any:
        """Execute a tool by name with validated arguments, path safety, and timeout enforcement."""
        spec = self._tools.get(name)
        if spec is None:
            raise ValueError(f"Tool '{name}' not found. Available: {self.list_tools()}")

        # Pydantic validation (preferred)
        if spec.input_model:
            try:
                parsed = spec.input_model(**kwargs)
                kwargs = parsed.model_dump()
            except ValidationError as exc:
                raise TypeError(f"Validation failed for tool '{name}': {exc}")

        # Fallback argument schema validation
        elif spec.argument_schema:
            for arg_name, expected_type in spec.argument_schema.items():
                if arg_name in kwargs and not isinstance(kwargs[arg_name], expected_type):
                    raise TypeError(
                        f"Argument '{arg_name}' for tool '{name}' must be of type {expected_type.__name__}, "
                        f"got {type(kwargs[arg_name]).__name__}"
                    )

        # Enforce global string length limits on all string kwargs
        for arg_name, arg_val in kwargs.items():
            if isinstance(arg_val, str) and len(arg_val) > TOOL_ARG_MAX_STRING_LENGTH:
                raise TypeError(
                    f"Argument '{arg_name}' for tool '{name}' exceeds maximum string length of {TOOL_ARG_MAX_STRING_LENGTH}"
                )

        # PRIV-002: Tool-argument logging for audit trail with privacy redaction
        safe_kwargs = safe_log_args(kwargs)
        audit_logger = logging.getLogger("gayatri.privacy.audit")
        audit_logger.info(f"TOOL_AUDIT: Tool '{name}' invoked with arguments: {safe_kwargs}")
        logger.info(f"Tool call: {name}(args=[{', '.join(kwargs.keys())}]) - values: {safe_kwargs}")
        # Enforce tool execution timeout (Audit #79)
        if spec.timeout_s and spec.timeout_s > 0:
            import concurrent.futures

            from core.agents.policy import CancellationToken, set_cancellation_token

            token = CancellationToken()

            def run_with_token():
                set_cancellation_token(token)
                try:
                    return spec.func(**kwargs)
                finally:
                    set_cancellation_token(None)

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(run_with_token)
                return future.result(timeout=spec.timeout_s)
            except concurrent.futures.TimeoutError as exc:
                token.cancel()
                logger.warning(f"Tool '{name}' timed out. Cancellation token set. Background thread may still be running if non-cooperative.")
                raise TimeoutError(f"Tool '{name}' execution timed out after {spec.timeout_s}s") from exc
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

        return spec.func(**kwargs)


class FileToolInput(BaseModel):
    """Base Pydantic model for tools that accept file paths."""

    @field_validator("*", mode="after")
    @classmethod
    def validate_paths(cls, value: Any, info: Any) -> Any:
        if not isinstance(value, str):
            return value

        field_name = info.field_name
        if any(k in field_name.lower() for k in ("path", "file", "dir")):
            import os
            from pathlib import Path

            from core.config import DATA_DIR

            # 1. Reject '..' entirely as a basic hygiene check
            if ".." in Path(value).parts:
                raise ValueError(
                    f"Path traversal detected in argument '{field_name}': parent directory traversal ('..') is strictly prohibited."
                )

            # 2. Strict bounds check against allowed directory
            allowed_dir = os.path.abspath(DATA_DIR)
            target_path = os.path.abspath(os.path.join(allowed_dir, value))
            try:
                if os.path.commonpath([allowed_dir, target_path]) != allowed_dir:
                    raise ValueError(
                        f"Path traversal detected in argument '{field_name}': Path {target_path} escapes allowed workspace {allowed_dir}."
                    )
            except ValueError:
                raise ValueError(
                    f"Path traversal detected in argument '{field_name}': Path {target_path} is on a different drive than workspace {allowed_dir}."
                )

        return value
# Global tool registry
tool_registry = ToolRegistry()


class AgentRuntime:
    """Runs agents: selects agent, processes request, handles tool calls."""

    def __init__(self, registry=None, tools=None):
        self.registry = registry or agent_registry
        self.tools = tools or tool_registry

    def process(self, user_message: str, context: AgentContext, spec: AgentSpec | None = None) -> AgentResponse:
        """Process a user message through the agent pipeline.

        1. Dispatch to the best matching agent (if spec not provided)
        2. Let the agent process (may include tool calls)
        3. Return the response
        """
        if spec is None:
            dispatch_result = self.registry.dispatch(user_message)
            if dispatch_result.is_ambiguous:
                alt_names = [m.spec.name for m in dispatch_result.alternatives[:2]]
                text = f"Your request is ambiguous. Did you mean to use the {alt_names[0]} or {alt_names[1]}?"
                return AgentResponse(text=text, agent_name="default", metadata={"ambiguous": True})

            if dispatch_result.primary is None:
                default_spec = self.registry.get_default_agent()
                if default_spec:
                    spec = default_spec
                else:
                    return AgentResponse(
                        text=self._default_response(user_message),
                        agent_name="default",
                    )
            else:
                spec = dispatch_result.primary.spec

        try:
            # 2. Instantiate and run the agent
            agent = self.registry.instantiate(spec.name)

            # 3. Process through agent loop (handle tool calls)
            response = self._agent_loop(agent, spec, context)
            return response
        except ModelUnavailableError as exc:
            logger.warning(f"Agent '{spec.name}' failed: local model is unavailable ({exc})")
            return AgentResponse(
                text=(
                    "The local AI model is not installed or unavailable. "
                    "Please download the model file to enable this agent."
                ),
                agent_name=spec.name,
                status="MODEL_UNAVAILABLE",
                metadata={"error": str(exc), "model_unavailable": True},
            )
        except Exception as exc:
            from core.errors import sanitize_error
            sanitized = sanitize_error(exc, category=f"agent_{spec.name}")
            return AgentResponse(
                text=f"Agent '{spec.name}' encountered an error: {sanitized.user_message} (Reference: {sanitized.diagnostic_id})",
                agent_name=spec.name,
                status="ERROR",
                metadata={"error": sanitized.user_message, "diagnostic_id": sanitized.diagnostic_id},
            )

    def _agent_loop(self, agent, spec: AgentSpec, context: AgentContext) -> AgentResponse:
        """Run the agent, handling tool calls in a loop with safety boundaries defined by policy."""
        import time

        start_time = time.time()
        step_count = 0
        total_tool_calls = 0
        total_tokens = 0

        # Base policy from spec, overridden by global settings if present
        from core.settings import get_settings
        settings = get_settings()

        policy = spec.policy
        max_steps = settings.get("agent.max_steps") or policy.max_steps
        time_budget_s = settings.get("agent.time_budget_s") or policy.time_budget_s
        token_budget = policy.token_budget
        tool_budget = policy.tool_budget

        response = agent.process(context)
        total_tokens += response.metadata.get("prompt_tokens", 0) + response.metadata.get("completion_tokens", 0)

        # Handle tool calls if the agent produced them
        while response.tool_calls and step_count < max_steps:
            # Enforce time budget
            if time.time() - start_time > time_budget_s:
                logger.warning(f"Agent '{spec.name}' tool loop exceeded time budget of {time_budget_s}s")
                break

            # Enforce token budget
            if token_budget is not None and total_tokens > token_budget:
                logger.warning(f"Agent '{spec.name}' tool loop exceeded token budget of {token_budget}")
                break

            # Enforce tool budget
            if total_tool_calls >= tool_budget:
                logger.warning(f"Agent '{spec.name}' tool loop exceeded tool budget of {tool_budget}")
                break

            step_count += 1
            tool_results = []

            calls_to_make = response.tool_calls
            if total_tool_calls + len(calls_to_make) > tool_budget:
                allowed = tool_budget - total_tool_calls
                logger.warning(f"Agent '{spec.name}' truncating {len(calls_to_make)} calls to {allowed} to fit budget")
                calls_to_make = calls_to_make[:allowed]

            total_tool_calls += len(calls_to_make)

            for tc in calls_to_make:
                tool_name = tc.get("tool", "")
                tool_args = tc.get("args", {})

                # Check if tool exists
                if tool_name not in self.tools.list_tools():
                    logger.warning(f"Agent requested unknown tool '{tool_name}'")
                    tool_results.append({
                        "tool": tool_name,
                        "error": f"Tool '{tool_name}' is not recognized or available.",
                    })
                    continue

                try:
                    result = self.tools.call(tool_name, **tool_args)
                    tool_results.append({"tool": tool_name, "result": str(result)})
                except Exception as exc:
                    # Sanitize error to prevent leaking internal stack trace or paths into model context
                    logger.error(f"Tool {tool_name} failed: {exc}")
                    tool_results.append({
                        "tool": tool_name,
                        "error": f"Tool execution failed: {type(exc).__name__}. Please verify arguments.",
                    })

            # Feed tool results back to the agent
            context.metadata["tool_results"] = tool_results
            response = agent.process(context)
            total_tokens += response.metadata.get("prompt_tokens", 0) + response.metadata.get("completion_tokens", 0)

        return response

    def _default_response(self, user_message: str) -> str:
        """Default response when no agent matches."""
        return (
            "I understand you're asking about something. I can help you with:\n"
            "• Learning programming — type /tutor or ask a coding question\n"
            "• Practicing skills — type /practice\n"
            "• Code review — type /review with your code\n"
            "• Document analysis — type /doc with a file\n\n"
            "What would you like to explore?"
        )
