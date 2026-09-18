import json

with open('training/datasets/chemistry/train.jsonl', 'r', encoding='utf-8') as f:
    lines = [f.readline() for _ in range(3)]

for i, line in enumerate(lines):
    ex = json.loads(line)
    print(f'--- Example {i+1} ---')
    print('Metadata:', json.dumps(ex.get('metadata', {}), indent=2))
    msgs = ex.get('messages', [])
    print('System:', msgs[0]['content'][:200] if msgs else 'N/A')
    print('User:', msgs[1]['content'][:200] if len(msgs) > 1 else 'N/A')
    print('Asst:', msgs[2]['content'][:200] if len(msgs) > 2 else 'N/A')
    print()
