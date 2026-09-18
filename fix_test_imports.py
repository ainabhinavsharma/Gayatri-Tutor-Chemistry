import re

for test_file in ['tests/test_model_unavailability.py', 'tests/test_regressions.py']:
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('from core.agents.default_agents', 'from legacy.agents.default_agents')
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
