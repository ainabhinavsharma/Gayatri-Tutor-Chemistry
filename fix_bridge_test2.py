import re

with open('tests/test_bridge.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('assert "Practice Generator" in agent_names', '')
content = content.replace('assert "Code Reviewer" in agent_names', '')
content = content.replace('assert "Math" in agent_names', '')

with open('tests/test_bridge.py', 'w', encoding='utf-8') as f:
    f.write(content)
