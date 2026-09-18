import re

with open('core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '        conv = self._get_conversation(session_id)\n\n        try:\n            mode = self._validate_mode(opts)',
    '        conv = self._get_conversation(session_id)\n\n        try:\n            mode = self._validate_mode(opts)\n            conv.mode = mode.value\n        '
)

content = content.replace(
    '        conv = self._get_conversation(session_id)\n\n        try:\n            mode_enum = self._validate_mode(opts)',
    '        conv = self._get_conversation(session_id)\n\n        try:\n            mode_enum = self._validate_mode(opts)\n            conv.mode = mode_enum.value\n        '
)

with open('core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)
