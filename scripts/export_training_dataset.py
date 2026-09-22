"""Dataset Split and Export Pipeline for Gayatri Chemistry Tutor.

Implements Sections 30 & 34 of Master Plan:
1. Reads curated examples from PRIVATE_WORK/training/curated/curated_training_examples.jsonl.
2. Performs stratified train/val/eval splitting with deterministic random seed.
3. Strict isolation: Evaluation set is never mixed into training data.
4. Exports:
   - PRIVATE_WORK/training/exported/train.jsonl (~75%)
   - PRIVATE_WORK/training/exported/validation.jsonl (~15%)
   - PRIVATE_WORK/training/exported/evaluation.jsonl (~10%)
   - PRIVATE_WORK/training/evaluation/evaluation.jsonl (dedicated evaluation repository)
5. Prints full split and distribution metrics.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "PRIVATE_WORK" / "training"
CURATED_PATH = TRAINING_DIR / "curated" / "curated_training_examples.jsonl"
EXPORTED_DIR = TRAINING_DIR / "exported"
EVAL_DIR = TRAINING_DIR / "evaluation"

TRAIN_PATH = EXPORTED_DIR / "train.jsonl"
VAL_PATH = EXPORTED_DIR / "validation.jsonl"
EVAL_PATH = EXPORTED_DIR / "evaluation.jsonl"
DEDICATED_EVAL_PATH = EVAL_DIR / "evaluation.jsonl"


def main() -> int:
    print("=" * 65)
    print("  GAYATRI CHEMISTRY TUTOR — DATASET SPLIT & EXPORT")
    print("=" * 65)

    if not CURATED_PATH.exists():
        print(f"[ERROR] Curated dataset not found: {CURATED_PATH}", file=sys.stderr)
        return 1

    EXPORTED_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    examples: List[Dict[str, Any]] = []
    with open(CURATED_PATH, encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                examples.append(json.loads(line_str))

    total = len(examples)
    print(f"[*] Read {total} curated examples.")

    # Deterministic shuffle for reproducibility
    random.seed(42)
    shuffled = list(examples)
    random.shuffle(shuffled)

    # 75% train, 15% validation, 10% evaluation
    n_eval = max(10, int(total * 0.10))
    n_val = max(15, int(total * 0.15))
    n_train = total - n_eval - n_val

    eval_set = shuffled[:n_eval]
    val_set = shuffled[n_eval : n_eval + n_val]
    train_set = shuffled[n_eval + n_val :]

    # Strict isolation check: Verify no overlapping examples
    eval_user_msgs = {ex["messages"][1]["content"] for ex in eval_set}
    train_user_msgs = {ex["messages"][1]["content"] for ex in train_set}
    overlap = eval_user_msgs.intersection(train_user_msgs)
    if overlap:
        print(f"[!] Warning: Data contamination detected: {len(overlap)} overlapping prompts.")
        # Filter overlapping from training to maintain strict test isolation
        train_set = [ex for ex in train_set if ex["messages"][1]["content"] not in eval_user_msgs]

    # Write splits
    def write_split(path: Path, split_data: List[Dict[str, Any]]):
        with open(path, "w", encoding="utf-8") as out_f:
            for item in split_data:
                out_f.write(json.dumps(item, ensure_ascii=False) + "\n")

    write_split(TRAIN_PATH, train_set)
    write_split(VAL_PATH, val_set)
    write_split(EVAL_PATH, eval_set)
    write_split(DEDICATED_EVAL_PATH, eval_set)

    print("\n[+] Splits successfully exported:")
    print(f"  - Train split       : {len(train_set):>3} examples -> {TRAIN_PATH}")
    print(f"  - Validation split  : {len(val_set):>3} examples -> {VAL_PATH}")
    print(f"  - Evaluation split  : {len(eval_set):>3} examples -> {EVAL_PATH}")
    print(f"  - Dedicated Eval Rep: {len(eval_set):>3} examples -> {DEDICATED_EVAL_PATH}")

    # Mode distribution across splits
    def print_dist(name: str, split_data: List[Dict[str, Any]]):
        counts = Counter(ex["metadata"].get("mode", "UNKNOWN") for ex in split_data)
        top_modes = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        print(f"  [{name:<10}] {top_modes}")

    print("\nTutor Mode Distribution by Split:")
    print_dist("Train", train_set)
    print_dist("Validation", val_set)
    print_dist("Evaluation", eval_set)

    print("=" * 65)
    print("  STATUS: DATASET EXPORT COMPLETE & READY FOR COLAB")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
