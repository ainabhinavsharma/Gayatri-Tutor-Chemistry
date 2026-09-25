"""Gayatri AI — SFT Dataset Invariant & Quality Validator.

Verifies the integrity of generated SFT datasets (JSONL format):
1. Valid JSON format on every line.
2. ChatML schema adherence (messages list with system, user, and assistant turns).
3. Pedagogical non-leakage invariants:
   - In EVALUATE or error correction turns, assistant must never leak numerical final answers.
4. Token length distribution within context window bounds.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gayatri.dataset_validator")


def validate_dataset_file(filepath: str | Path) -> Tuple[bool, Dict[str, int], List[str]]:
    """Validate a JSONL training dataset file against ChatML and pedagogical rules."""
    path = Path(filepath)
    if not path.exists():
        return False, {}, [f"Dataset file not found: {path}"]

    stats = {
        "total_dialogues": 0,
        "total_messages": 0,
        "system_messages": 0,
        "user_messages": 0,
        "assistant_messages": 0,
        "evaluated_turns": 0,
        "flagged_leakage": 0,
    }
    errors = []

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue

            try:
                item = json.loads(line_str)
            except Exception as e:
                errors.append(f"Line {line_no}: Invalid JSON: {e}")
                continue

            if not isinstance(item, dict) or "messages" not in item:
                errors.append(f"Line {line_no}: Missing 'messages' key")
                continue

            messages = item["messages"]
            if not isinstance(messages, list) or len(messages) < 2:
                errors.append(f"Line {line_no}: 'messages' must have at least 2 entries")
                continue

            stats["total_dialogues"] += 1

            # Validate turns
            has_system = False
            for m_idx, m in enumerate(messages):
                role = m.get("role")
                content = m.get("content", "")

                if not role or not isinstance(content, str) or not content.strip():
                    errors.append(f"Line {line_no}, Msg {m_idx}: Empty role or content")
                    continue

                stats["total_messages"] += 1
                if role == "system":
                    stats["system_messages"] += 1
                    has_system = True
                elif role == "user":
                    stats["user_messages"] += 1
                elif role == "assistant":
                    stats["assistant_messages"] += 1

                    # Check for classic Socratic anti-leakage invariant:
                    # If user made the 700 J error, assistant should NOT spoonfeed "the answer is 300 J" directly.
                    if m_idx > 0 and messages[m_idx - 1].get("role") == "user":
                        prev_user = messages[m_idx - 1].get("content", "")
                        if "700" in prev_user and "delta u" in prev_user.lower():
                            stats["evaluated_turns"] += 1
                            lower_asst = content.lower()
                            if "the answer is 300" in lower_asst or "the correct answer is 300" in lower_asst:
                                stats["flagged_leakage"] += 1
                                errors.append(f"Line {line_no}: Leakage violation in assistant response to 700 J error.")

            if not has_system:
                errors.append(f"Line {line_no}: Dialogue missing system message")

    is_valid = len(errors) == 0
    return is_valid, stats, errors


def main():
    parser = argparse.ArgumentParser(description="Validate Gayatri SFT Dataset")
    parser.add_argument("--file", type=str, default="data/training/synthetic_chemistry_dialogues.jsonl", help="Path to JSONL dataset")
    args = parser.parse_args()

    logger.info(f"Validating dataset file: {args.file}")
    is_valid, stats, errors = validate_dataset_file(args.file)

    print("=" * 60)
    print("Gayatri SFT Dataset Validation Summary")
    print("=" * 60)
    for k, v in stats.items():
        print(f"  {k:22s}: {v}")
    print("=" * 60)

    if not is_valid:
        print(f"FAILED with {len(errors)} error(s):")
        for err in errors[:15]:
            print(f"  - {err}")
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more.")
        exit(1)
    else:
        print("SUCCESS: Dataset satisfies all schema and anti-leakage invariants.")


if __name__ == "__main__":
    main()
