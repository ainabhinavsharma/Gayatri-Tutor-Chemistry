import re

with open('core/session.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);\n            """)\n\n        def add_mode_and_user_id(c):',
    'CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);\n\n                CREATE TABLE IF NOT EXISTS tutor_contexts (\n                    session_id  TEXT PRIMARY KEY,\n                    state_json  TEXT NOT NULL,\n                    updated_at  TEXT NOT NULL,\n                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE\n                );\n            """)\n\n        def add_mode_and_user_id(c):'
)

with open('core/session.py', 'w', encoding='utf-8') as f:
    f.write(content)
