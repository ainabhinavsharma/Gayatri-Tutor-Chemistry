import re

with open('tests/test_curriculum_loader.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'graph = LearningDependencyGraph(db_path=":memory:")',
    'graph = LearningDependencyGraph(db_path=":memory:")\n        graph._create_schema()'
)

with open('tests/test_curriculum_loader.py', 'w', encoding='utf-8') as f:
    f.write(content)
