import re

with open('app/bridge/facade.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'def send_message(self, message: str, agent_name: str = ""):',
    'def send_message(self, message: str, mode: str = "general_assistant"):'
)
content = content.replace(
    'opts = TurnOptions(forced_agent=agent_name)',
    'opts = TurnOptions(mode=mode)'
)
content = content.replace(
    'if agent_name and agent_name.lower() != "auto":',
    'if mode and mode.lower() != "auto":'
)

with open('app/bridge/facade.py', 'w', encoding='utf-8') as f:
    f.write(content)
