import re

with open('training/generate_data.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update generate_tutoring_examples
code = code.replace('for user_msg, assistant_msg in TUTORING_QA:', 'for idx, (user_msg, assistant_msg) in enumerate(TUTORING_QA):')
code = code.replace('''            examples.append({
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ]
            })''', '''            examples.append({
                "source_family": f"tutor_qa_{idx}",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ]
            })''')

code = code.replace('''                examples.append({
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ]
                })''', '''                examples.append({
                    "source_family": f"tutor_topic_{topic}",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ]
                })''')

code = code.replace('for _ in range(400):', 'for idx in range(400):')
code = code.replace('''        examples.append({
            "messages": [
                {"role": "system", "content": random.choice(TUTOR_SYSTEMS)},
                {"role": "user", "content": follow_q},
                {"role": "assistant", "content": answer},
            ]
        })''', '''        # Group by the specific follow-up template structure to avoid leakage
        template_idx = follow_up_templates.index(next(t for t in follow_up_templates if t[0] == follow_q or "{wrong}" in t[0] and t[0].replace("{wrong}", "") in follow_q))
        examples.append({
            "source_family": f"tutor_followup_{template_idx}",
            "messages": [
                {"role": "system", "content": random.choice(TUTOR_SYSTEMS)},
                {"role": "user", "content": follow_q},
                {"role": "assistant", "content": answer},
            ]
        })''')

# 2. Update generate_agent_examples
code = code.replace('''            examples.append({
                "messages": [
                    {"role": "system", "content": AGENT_SYSTEM},
                    {"role": "user", "content": trigger},
                    {"role": "assistant", "content": f"[AGENT:{agent_name}]\\n{task_descriptions[agent_name]}"},
                ]
            })''', '''            examples.append({
                "source_family": f"agent_trigger_{agent_name}",
                "messages": [
                    {"role": "system", "content": AGENT_SYSTEM},
                    {"role": "user", "content": trigger},
                    {"role": "assistant", "content": f"[AGENT:{agent_name}]\\n{task_descriptions[agent_name]}"},
                ]
            })''')

code = code.replace('for _ in range(600):', 'for idx in range(600):')
code = code.replace('''        examples.append({
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": f"[AGENT:{agent_name}]\\n{task_descs[agent_name]}"},
            ]
        })''', '''        examples.append({
            "source_family": f"agent_dispatch_{agent_name}",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": f"[AGENT:{agent_name}]\\n{task_descs[agent_name]}"},
            ]
        })''')

code = code.replace('for q, a in direct_qas:', 'for idx, (q, a) in enumerate(direct_qas):')
code = code.replace('''        examples.append({
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ]
        })''', '''        examples.append({
            "source_family": f"agent_direct_{idx}",
            "messages": [
                {"role": "system", "content": AGENT_SYSTEM},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ]
        })''')

# 3. Update generate_conversations
code = code.replace('for conv in conv_templates:', 'for idx, conv in enumerate(conv_templates):')
code = code.replace('''        conversations.append({"messages": [{"role": "system", "content": system}] + messages})''', '''        conversations.append({
            "source_family": f"conv_{idx}",
            "messages": [{"role": "system", "content": system}] + messages
        })''')


# 4. Update main
main_new = '''
def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(output_dir, "processed")
    os.makedirs(data_dir, exist_ok=True)

    print("Generating tutoring data...")
    tutoring = generate_tutoring_examples()
    print(f"  {len(tutoring)} examples")

    print("Generating agent orchestration data...")
    agent = generate_agent_examples()
    print(f"  {len(agent)} examples")

    print("Generating conversations...")
    convs = generate_conversations()
    print(f"  {len(convs)} conversations")

    all_data = tutoring + agent + convs
    total = len(all_data)
    print(f"Total: {total} examples")

    # Group by source_family
    families = {}
    for item in all_data:
        family = item.get("source_family", "unknown")
        families.setdefault(family, []).append(item)
    
    # Shuffle families securely
    family_keys = list(families.keys())
    random.seed(42)
    random.shuffle(family_keys)

    # Split 90/10 by families
    train_data = []
    val_data = []
    target_train = int(total * 0.9)

    for fk in family_keys:
        if len(train_data) < target_train:
            train_data.extend(families[fk])
        else:
            val_data.extend(families[fk])
            
    # Remove source_family before saving, but we can write manifest
    def strip_family(d):
        return {"messages": d["messages"]}

    train_path = os.path.join(data_dir, "train.jsonl")
    val_path = os.path.join(data_dir, "val.jsonl")
    manifest_path = os.path.join(data_dir, "manifest.json")

    with open(train_path, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(strip_family(item), ensure_ascii=False) + "\\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(strip_family(item), ensure_ascii=False) + "\\n")
            
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_examples": total,
            "train_examples": len(train_data),
            "val_examples": len(val_data),
            "total_families": len(families),
            "train_families": sum(1 for fk in family_keys if families[fk][0] in train_data),
            "val_families": sum(1 for fk in family_keys if families[fk][0] in val_data),
            "split_ratio": len(train_data) / total
        }, f, indent=2)

    print(f"\\nWrote {len(train_data)} training examples to {train_path}")
    print(f"Wrote {len(val_data)} validation examples to {val_path}")
    print(f"Wrote manifest to {manifest_path}")
    print("\\nDataset ready for Colab training!")
'''

code = re.sub(r'def main\(\):.*?(?=if __name__ == "__main__":)', main_new + '\n\n', code, flags=re.DOTALL)

with open('training/generate_data.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Patched generate_data.py")
