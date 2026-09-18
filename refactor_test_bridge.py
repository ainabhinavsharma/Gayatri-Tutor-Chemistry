import re

with open('tests/test_bridge.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'bridge.send_message("Review this snippet", "Code Reviewer")',
    'bridge.send_message("Review this snippet", "chemistry_tutor")'
)
content = content.replace(
    'assert opts.forced_agent == "Code Reviewer"',
    'assert opts.mode == "chemistry_tutor"'
)

with open('tests/test_bridge.py', 'w', encoding='utf-8') as f:
    f.write(content)
