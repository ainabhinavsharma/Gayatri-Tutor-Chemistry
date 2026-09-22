"""Training Dataset Validator for Gayatri Chemistry Tutor.

Implements validation suite per Sections 31 & 50 of Master Plan:
1. Validates JSON and JSONL compliance.
2. Enforces chat format schema (roles: system, user, assistant).
3. Verifies metadata completeness (topic, concept, mode, quality).
4. Scans for PII or private identifier leakage.
5. Scans for raw stacktraces or leaked debug tokens.
6. Returns exit code 0 (PASS) or 1 (FAIL).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURATED_PATH = PROJECT_ROOT / "PRIVATE_WORK" / "training" / "curated" / "curated_training_examples.jsonl"

VALID_ROLES = {"system", "user", "assistant"}
REQUIRED_METADATA_KEYS = {"topic", "concept", "mode", "quality"}

# PII and Debug leak patterns
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "Email address detected"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "Phone number detected"),
    (r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "IP address detected (except localhost)", lambda m: m.group(0) != "127.0.0.1"),
    (r"[C-Z]:\\(?:Users|home)\\[^\s]+", "Local user path detected"),
    (r"Traceback \(most recent call last\):", "Python traceback detected"),
]


def validate_example(idx: int, obj: dict) -> List[str]:
    """Validate a single training example against schema and safety checks."""
    errors = []

    # 1. Message list check
    messages = obj.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        errors.append(f"Line {idx}: 'messages' must be a list with at least 2 messages.")
        return errors

    has_user = False
    has_assistant = False

    for m_idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            errors.append(f"Line {idx}, msg {m_idx}: Message must be a dictionary.")
            continue
        role = msg.get("role")
        content = msg.get("content")

        if role not in VALID_ROLES:
            errors.append(f"Line {idx}, msg {m_idx}: Invalid role '{role}'. Allowed: {VALID_ROLES}")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"Line {idx}, msg {m_idx}: Content must be a non-empty string.")

        if role == "user":
            has_user = True
        elif role == "assistant":
            has_assistant = True

        # PII and Debug leak checks
        if isinstance(content, str):
            for pat_info in PII_PATTERNS:
                regex, desc = pat_info[0], pat_info[1]
                cond = pat_info[2] if len(pat_info) > 2 else lambda m: True
                for match in re.finditer(regex, content):
                    if cond(match):
                        errors.append(f"Line {idx}, msg {m_idx}: {desc} -> '{match.group(0)}'")

    if not has_user:
        errors.append(f"Line {idx}: Missing 'user' turn.")
    if not has_assistant:
        errors.append(f"Line {idx}: Missing 'assistant' turn.")

    # 2. Metadata check
    metadata = obj.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"Line {idx}: Missing or invalid 'metadata' dictionary.")
    else:
        missing_keys = REQUIRED_METADATA_KEYS - set(metadata.keys())
        if missing_keys:
            errors.append(f"Line {idx}: Missing required metadata keys: {missing_keys}")
        if metadata.get("quality") != "approved":
            errors.append(f"Line {idx}: Metadata 'quality' must be 'approved', got '{metadata.get('quality')}'.")

    return errors


def main() -> int:
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CURATED_PATH

    print("=" * 65)
    print("  GAYATRI CHEMISTRY TUTOR — TRAINING DATASET VALIDATOR")
    print("=" * 65)
    print(f"[*] Validating target file: {target_path}")

    if not target_path.exists():
        print(f"[ERROR] Target file does not exist: {target_path}", file=sys.stderr)
        return 1

    total_examples = 0
    all_errors: List[str] = []
    mode_distribution: Counter = Counter()
    topic_distribution: Counter = Counter()

    with open(target_path, encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            total_examples += 1
            try:
                obj = json.loads(line_str)
            except json.JSONDecodeError as exc:
                all_errors.append(f"Line {idx}: Invalid JSON syntax - {exc}")
                continue

            errs = validate_example(idx, obj)
            all_errors.extend(errs)

            meta = obj.get("metadata", {})
            mode_distribution[meta.get("mode", "UNKNOWN")] += 1
            topic_distribution[meta.get("topic", "UNKNOWN")] += 1

    print(f"[*] Total parsed examples : {total_examples}")
    print(f"[*] Total validation errors: {len(all_errors)}")

    if all_errors:
        print("\n[!] Validation Failed with errors:")
        for err in all_errors[:15]:
            print(f"    - {err}")
        if len(all_errors) > 15:
            print(f"    ... and {len(all_errors) - 15} more errors.")
        return 1

    print("\n[+] Verification Check: PASSED (0 errors)")
    print("\nValidated Mode Breakdown:")
    for mode, count in sorted(mode_distribution.items()):
        print(f"  {mode:<20}: {count:>3} examples")

    print("\nValidated Topic Breakdown:")
    for topic, count in sorted(topic_distribution.items()):
        print(f"  {topic:<20}: {count:>3} examples")

    print("=" * 65)
    print("  STATUS: DATASET FULLY VALID & READY FOR COLAB EXPORT")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
