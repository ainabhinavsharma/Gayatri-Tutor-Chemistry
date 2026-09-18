import re

with open('tests/test_curriculum_loader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# _create_schema is already called in __init__, so issue must be :memory: not initializing
# Let's use a temp file instead
content = content.replace(
    'graph = LearningDependencyGraph(db_path=":memory:")\n        graph._create_schema()',
    'import tempfile, os\n        tmp = tempfile.mktemp(suffix=".db")\n        graph = LearningDependencyGraph(db_path=tmp)'
)

with open('tests/test_curriculum_loader.py', 'w', encoding='utf-8') as f:
    f.write(content)
