import re

with open('core/runtimes/chemistry.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('from core.agents.default_agents', 'from legacy.agents.default_agents')
with open('core/runtimes/chemistry.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('core/runtimes/general.py', 'r', encoding='utf-8') as f:
    content2 = f.read()
content2 = content2.replace('from core.agents.default_agents', 'from legacy.agents.default_agents')
with open('core/runtimes/general.py', 'w', encoding='utf-8') as f:
    f.write(content2)
