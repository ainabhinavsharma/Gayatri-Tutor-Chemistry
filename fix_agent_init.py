import re

with open('core/agents/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from core.agents.default_agents import register_default_agents', '')
content = content.replace('from core.agents.prompt_agents import register_prompt_agents', '')

with open('core/agents/__init__.py', 'w', encoding='utf-8') as f:
    f.write(content)
