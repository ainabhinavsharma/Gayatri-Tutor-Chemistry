import json
from collections import Counter, defaultdict

with open('training/datasets/chemistry/train.jsonl', 'r', encoding='utf-8') as f:
    examples = [json.loads(line) for line in f]

domains = Counter()
topics = Counter()
interaction_types = Counter()
difficulties = Counter()
q_types = Counter()
class_levels = Counter()

for ex in examples:
    m = ex.get('metadata', {})
    domains[m.get('domain', 'N/A')] += 1
    topics[m.get('topic_id', 'N/A')] += 1
    interaction_types[m.get('interaction_type', 'N/A')] += 1
    difficulties[m.get('difficulty', 'N/A')] += 1
    q_types[m.get('question_type', 'N/A')] += 1
    class_levels[m.get('class_level', 'N/A')] += 1

print(f'Total train examples: {len(examples)}')
print(f'\nDomains: {dict(domains)}')
print(f'\nTop topics: {dict(topics.most_common(10))}')
print(f'\nInteraction types: {dict(interaction_types)}')
print(f'\nDifficulties: {dict(sorted(difficulties.items()))}')
print(f'\nQuestion types: {dict(q_types)}')
print(f'\nClass levels: {dict(class_levels)}')
