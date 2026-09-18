import re

with open('core/conversation.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'class Conversation:\n    """Conversation history for one session.\n    \n    Retains full conversation history for UI and persistence (up to max_history turns),\n    while get_messages_for_model() provides a trimmed rolling window bounded by max_messages\n    for LLM prompt context.\n    """\n    session_id: str',
    'class Conversation:\n    """Conversation history for one session.\n    \n    Retains full conversation history for UI and persistence (up to max_history turns),\n    while get_messages_for_model() provides a trimmed rolling window bounded by max_messages\n    for LLM prompt context.\n    """\n    session_id: str\n    mode: str = "general_assistant"\n    user_id: str = "local_user_1"'
)

with open('core/conversation.py', 'w', encoding='utf-8') as f:
    f.write(content)
