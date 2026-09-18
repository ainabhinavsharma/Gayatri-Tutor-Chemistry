import re

with open('app/bridge/facade.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'def get_agents\(self\) -> str:.*?return json\.dumps\(result\)',
    'def get_agents(self) -> str:\n        return "[]"',
    content,
    flags=re.DOTALL
)

with open('app/bridge/facade.py', 'w', encoding='utf-8') as f:
    f.write(content)
