import re

with open('app/bridge/facade.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('def _get_orchestrator(self):', 'def _get_orchestrator(self):\n        from core.agents.registry import agent_registry\n')

with open('app/bridge/facade.py', 'w', encoding='utf-8') as f:
    f.write(content)
