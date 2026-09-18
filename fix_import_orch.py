import re

with open('app/bridge/facade.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'from core.orchestrator import Orchestrator' not in content:
    content = content.replace('def _get_orchestrator(self):', 'def _get_orchestrator(self):\n        from core.orchestrator import Orchestrator\n')
    
    with open('app/bridge/facade.py', 'w', encoding='utf-8') as f:
        f.write(content)

with open('tests/test_agent_matching.py', 'r', encoding='utf-8') as f:
    content = f.read()
    content = content.replace('from core.agents.default_agents', 'from legacy.agents.default_agents')
    content = content.replace('from core.agents.prompt_agents', 'from legacy.agents.prompt_agents')

with open('tests/test_agent_matching.py', 'w', encoding='utf-8') as f:
    f.write(content)
