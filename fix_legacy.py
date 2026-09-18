import re

with open('legacy/agents/default_agents.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from core.agents.prompt_agents', 'from legacy.agents.prompt_agents')

with open('legacy/agents/default_agents.py', 'w', encoding='utf-8') as f:
    f.write(content)
