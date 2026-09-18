import re

with open('core/agents/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('register_default_agents()', '')

with open('core/agents/__init__.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('app/bridge/facade.py', 'r', encoding='utf-8') as f:
    content2 = f.read()

content2 = re.sub(
    r'from core\.agents\.default_agents import register_default_agents.*?register_default_agents\(\)',
    '',
    content2,
    flags=re.DOTALL
)

with open('app/bridge/facade.py', 'w', encoding='utf-8') as f:
    f.write(content2)

