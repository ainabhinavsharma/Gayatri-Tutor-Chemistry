import re

with open('app/ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove HTML element
content = re.sub(
    r'<div\s+class="field-row">.*?<select\s+id="agent-selector">.*?</select>.*?</div>',
    '',
    content,
    flags=re.DOTALL
)

# Replace JS references
content = re.sub(r'var\s+selectedAgent\s*=\s*document\.getElementById\("agent-selector"\)\.value;', 'var selectedAgent = "chemistry_tutor";', content)

with open('app/ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
