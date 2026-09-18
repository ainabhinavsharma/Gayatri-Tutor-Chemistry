import json
import os
import argparse
import re

def get_text_signature(messages):
    """Create a normalized string of the first user message for near-duplicate detection."""
    for m in messages:
        if m.get("role") == "user":
            text = m.get("content", "").lower()
            # Remove punctuation and extra whitespace
            text = re.sub(r'[^\w\s]', '', text)
            words = text.split()
            return " ".join(words)
    return ""

def deduplicate(input_path, output_path, report_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    seen_exact_texts = set()
    unique_examples = []
    
    stats = {
        "total_processed": 0,
        "unique_kept": 0,
        "exact_duplicates_removed": 0,
        "near_duplicates_removed": 0
    }
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            stats["total_processed"] += 1
            
            data = json.loads(line)
            signature = get_text_signature(data.get("messages", []))
            
            if signature in seen_exact_texts:
                stats["exact_duplicates_removed"] += 1
            else:
                seen_exact_texts.add(signature)
                unique_examples.append(data)
                stats["unique_kept"] += 1
                
    with open(output_path, 'w', encoding='utf-8') as f_out:
        for ex in unique_examples:
            f_out.write(json.dumps(ex) + "\n")
            
    with open(report_path, 'w', encoding='utf-8') as f_rep:
        json.dump(stats, f_rep, indent=2)
        
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    
    stats = deduplicate(args.input, args.output, args.report)
    print(f"Deduplication complete. Kept {stats['unique_kept']}/{stats['total_processed']}. Report saved to {args.report}")
