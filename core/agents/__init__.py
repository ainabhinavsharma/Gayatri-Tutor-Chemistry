"""Gayatri AI — Agents package."""

# Register all default and prompt-engineered agents (idempotent)
from core.agents.default_agents import register_default_agents
from core.agents.prompt_agents import register_prompt_agents
from core.agents.registry import AgentResponse, AgentSpec, agent_registry
from core.agents.runtime import AgentContext, AgentRuntime, ToolRegistry, tool_registry

register_default_agents()
register_prompt_agents()

__all__ = [
    "AgentContext",
    "AgentResponse",
    "AgentRuntime",
    "AgentSpec",
    "ToolRegistry",
    "agent_registry",
    "register_prompt_agents",
    "tool_registry",
]
