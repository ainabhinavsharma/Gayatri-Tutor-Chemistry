import re

test_file = 'tests/test_model_unavailability.py'
with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from core.agents.prompt_agents', 'from legacy.agents.prompt_agents')

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(content)
