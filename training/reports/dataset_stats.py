import json
import os
import argparse

def compute_stats(directory):
    files = ["train.jsonl", "validation.jsonl", "test.jsonl", "evaluation.jsonl"]
    
    overall_stats = {
        "total_examples": 0,
        "domains": {},
        "interaction_types": {},
        "question_types": {},
        "difficulty_distribution": {},
        "class_levels": {}
    }
    
    for filename in files:
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                meta = data.get("metadata", {})
                
                overall_stats["total_examples"] += 1
                
                # Domain
                domain = meta.get("domain", "unknown")
                overall_stats["domains"][domain] = overall_stats["domains"].get(domain, 0) + 1
                
                # Interaction Type
                interaction = meta.get("interaction_type", "unknown")
                overall_stats["interaction_types"][interaction] = overall_stats["interaction_types"].get(interaction, 0) + 1
                
                # Question Type
                qtype = meta.get("question_type", "unknown")
                overall_stats["question_types"][qtype] = overall_stats["question_types"].get(qtype, 0) + 1
                
                # Difficulty
                diff = str(meta.get("difficulty", "unknown"))
                overall_stats["difficulty_distribution"][diff] = overall_stats["difficulty_distribution"].get(diff, 0) + 1
                
                # Class Level
                cls_level = meta.get("class_level", "unknown")
                overall_stats["class_levels"][cls_level] = overall_stats["class_levels"].get(cls_level, 0) + 1
                
    return overall_stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="../datasets/chemistry")
    parser.add_argument("--out", default="dataset_statistics.json")
    args = parser.parse_args()
    
    stats = compute_stats(os.path.abspath(args.dir))
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
        
    print(f"Dataset statistics generated at {out_path}")
