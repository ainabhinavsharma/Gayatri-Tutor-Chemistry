import re

with open('app/bridge/chat.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'def send_message(self, message: str, agent_name: str = ""):',
    'def send_message(self, message: str, mode: str = "general_assistant"):'
)
content = content.replace(
    'self.facade.send_message(message, agent_name)',
    'self.facade.send_message(message, mode)'
)

with open('app/bridge/chat.py', 'w', encoding='utf-8') as f:
    f.write(content)
