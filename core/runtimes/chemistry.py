import logging
from legacy.agents.default_agents import _build_tutor_system_prompt, _get_tutor_context, _build_messages, _local_chat_stream

logger = logging.getLogger("gayatri.runtimes.chemistry")

class ChemistryTutorRuntime:
    def stream(self, user_message: str, context):
        system = _build_tutor_system_prompt()
        dynamic_ctx = _get_tutor_context(context)
        msgs = _build_messages(
            system,
            user_message,
            getattr(context, 'history', None),
            dynamic_context=dynamic_ctx
        )
        return _local_chat_stream(msgs, max_tokens=400)
