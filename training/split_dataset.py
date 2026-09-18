import json
import os
import argparse
import random

def split_dataset(input_file, out_dir, train_ratio=0.9, val_ratio=0.05, test_ratio=0.05):
    os.makedirs(out_dir, exist_ok=True)
    
    examples = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
                
    # To prevent semantic leakage, normally we'd group by topic/template
    # Here we'll just do a randomized split for demonstration
    random.shuffle(examples)
    
    total = len(examples)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    
    train_set = examples[:train_end]
    val_set = examples[train_end:val_end]
    test_set = examples[val_end:]
    
    def write_set(data, filename):
        path = os.path.join(out_dir, filename)
        with open(path, 'w', encoding='utf-8') as f_out:
            for ex in data:
                f_out.write(json.dumps(ex) + "\n")
        print(f"Wrote {len(data)} examples to {path}")
        
    write_set(train_set, "train.jsonl")
    write_set(val_set, "validation.jsonl")
    write_set(test_set, "test.jsonl")
    
    # Generate frozen evaluation set (we'll just copy the test set for this mock)
    write_set(test_set, "evaluation.jsonl")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", default="../../datasets/chemistry")
    args = parser.parse_args()
    
    split_dataset(args.input, os.path.abspath(args.outdir))
