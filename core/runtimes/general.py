import logging
from legacy.agents.default_agents import _build_messages, _local_chat_stream
from core.settings import get_settings

logger = logging.getLogger("gayatri.runtimes.general")

class GeneralAssistantRuntime:
    def stream(self, user_message: str, context):
        sys_prompt = get_settings().get("system_prompt", "You are Gayatri AI, a helpful learning assistant.")
        msgs = _build_messages(
            sys_prompt,
            user_message,
            getattr(context, 'history', None)
        )
        return _local_chat_stream(msgs, max_tokens=400)
