import re

with open('app/bridge/facade.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'sessions = store.list_sessions()',
    'sessions = store.list_sessions(mode="chemistry_tutor", user_id="local_user_1")'
)

with open('app/bridge/facade.py', 'w', encoding='utf-8') as f:
    f.write(content)
