import re

with open('core/session.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _create_schema and the try-except with a proper migration system
new_schema = '''
    def _create_schema(self) -> None:
        """Create or migrate tables."""
        from core.db import run_migrations
        conn = self.conn
        
        def initial_schema(c):
            c.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id          TEXT PRIMARY KEY,
                    profile_id  TEXT DEFAULT 'default',
                    title       TEXT DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    agent_name  TEXT DEFAULT '',
                    timestamp   TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            """)

        def add_mode_and_user_id(c):
            try:
                c.execute("ALTER TABLE sessions ADD COLUMN mode TEXT DEFAULT 'general_assistant';")
            except Exception:
                pass
            try:
                c.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT DEFAULT 'local_user_1';")
            except Exception:
                pass
            c.execute("UPDATE sessions SET mode = 'general_assistant' WHERE mode IS NULL;")
            c.execute("UPDATE sessions SET user_id = 'local_user_1' WHERE user_id IS NULL;")
        
        migrations = {
            1: ("initial_schema", initial_schema),
            2: ("add_mode_and_user_id", add_mode_and_user_id),
        }
        
        run_migrations(conn, migrations)
'''

content = re.sub(
    r'    def _create_schema\(self\) -> None:.*?        except sqlite3\.OperationalError:\n            pass',
    new_schema.strip('\n'),
    content,
    flags=re.DOTALL
)

with open('core/session.py', 'w', encoding='utf-8') as f:
    f.write(content)
