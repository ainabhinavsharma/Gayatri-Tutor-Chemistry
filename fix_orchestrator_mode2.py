import re

with open('core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('conv.mode = mode.value', 'conv.mode = mode')
content = content.replace('conv.mode = mode_enum.value', 'conv.mode = mode_enum')

with open('core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)
