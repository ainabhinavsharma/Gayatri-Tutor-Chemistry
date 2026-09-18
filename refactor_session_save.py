import re

with open('core/session.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'def save_session(self, session_id: str, conversation: Any, tutor_context: Any = None, mode: str = "general_assistant", user_id: str = "local_user_1") -> None:',
    'def save_session(self, session_id: str, conversation: Any, tutor_context: Any = None) -> None:'
)
content = content.replace(
    'self._enqueue_write(\n            self._save_session_internal,\n            session_id, title, messages, tutor_context, mode, user_id\n        )',
    'mode = getattr(conversation, "mode", "general_assistant")\n        user_id = getattr(conversation, "user_id", "local_user_1")\n        self._enqueue_write(\n            self._save_session_internal,\n            session_id, title, messages, tutor_context, mode, user_id\n        )'
)

with open('core/session.py', 'w', encoding='utf-8') as f:
    f.write(content)
