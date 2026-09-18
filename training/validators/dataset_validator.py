import re
import json
from typing import List, Dict, Any

class ValidationError(Exception):
    pass

class EmptyMessageCheck:
    def check(self, item: Dict[str, Any], idx: int) -> None:
        for msg in item.get('messages', []):
            if not msg.get('content') or not str(msg['content']).strip():
                raise ValidationError(f"Item {idx} has an empty message")

class RoleCheck:
    def check(self, item: Dict[str, Any], idx: int) -> None:
        allowed = {'system', 'user', 'assistant', 'tool'}
        for msg in item.get('messages', []):
            role = msg.get('role')
            if role not in allowed:
                raise ValidationError(f"Item {idx} has invalid role '{role}'")

class DuplicateCheck:
    def __init__(self):
        self.seen = set()
        
    def check(self, item: Dict[str, Any], idx: int) -> None:
        sig = json.dumps(item.get('messages', []), sort_keys=True)
        if sig in self.seen:
            raise ValidationError(f"Item {idx} is a duplicate")
        self.seen.add(sig)

class ConflictCheck:
    def __init__(self):
        self.contexts = {}
        
    def check(self, item: Dict[str, Any], idx: int) -> None:
        msgs = item.get('messages', [])
        for i in range(len(msgs)):
            if msgs[i].get('role') == 'assistant':
                ctx = json.dumps(msgs[:i], sort_keys=True)
                target = msgs[i].get('content')
                if ctx in self.contexts and self.contexts[ctx] != target:
                    raise ValidationError(f"Item {idx} has conflicting target for same context")
                self.contexts[ctx] = target

class LengthCheck:
    def check(self, item: Dict[str, Any], idx: int) -> None:
        chars = sum(len(str(msg.get('content', ''))) for msg in item.get('messages', []))
        if chars > 32000:
            raise ValidationError(f"Item {idx} exceeds length limit: {chars} chars")

class PIICheck:
    EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    PHONE_RE = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    
    def check(self, item: Dict[str, Any], idx: int) -> None:
        for msg in item.get('messages', []):
            content = str(msg.get('content', ''))
            if self.EMAIL_RE.search(content):
                raise ValidationError(f"Item {idx} contains PII (email)")
            if self.PHONE_RE.search(content):
                raise ValidationError(f"Item {idx} contains PII (phone)")

class CodeFenceCheck:
    def check(self, item: Dict[str, Any], idx: int) -> None:
        for msg in item.get('messages', []):
            content = str(msg.get('content', ''))
            if content.count('```') % 2 != 0:
                raise ValidationError(f"Item {idx} has unclosed code fences")

class DatasetValidator:
    def __init__(self):
        self.checks = [
            EmptyMessageCheck(),
            RoleCheck(),
            DuplicateCheck(),
            ConflictCheck(),
            LengthCheck(),
            PIICheck(),
            CodeFenceCheck(),
        ]
        
    def validate_item(self, item: Dict[str, Any], idx: int) -> List[str]:
        errors = []
        for check in self.checks:
            try:
                check.check(item, idx)
            except ValidationError as e:
                errors.append(str(e))
        return errors

    def validate_dataset(self, data: List[Dict[str, Any]]) -> List[str]:
        all_errors = []
        for idx, item in enumerate(data):
            all_errors.extend(self.validate_item(item, idx))
        return all_errors


def extract_shingles(text: str, n: int = 3) -> set[tuple[str, ...]]:
    """Extract word n-grams for Jaccard similarity comparison (Audit #TRAIN-002)."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i+n]) for i in range(len(words) - n + 1)}


def jaccard_similarity(s1: set, s2: set) -> float:
    """Calculate Jaccard similarity coefficient between two token sets."""
    if not s1 or not s2:
        return 0.0
    intersection = len(s1.intersection(s2))
    union = len(s1.union(s2))
    return intersection / union if union > 0 else 0.0


class SplitLeakageCheck:
    """Checks for exact and near-duplicate leakage between training and validation splits (Audit #TRAIN-002)."""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def check_splits(
        self, train_data: List[Dict[str, Any]], val_data: List[Dict[str, Any]]
    ) -> List[str]:
        """Verify that no sample in val_data is a duplicate or near-duplicate of train_data."""
        leakage_errors = []
        train_shingles = []
        for i, item in enumerate(train_data):
            text = " ".join(str(m.get("content", "")) for m in item.get("messages", []))
            train_shingles.append((i, extract_shingles(text)))

        for j, val_item in enumerate(val_data):
            val_text = " ".join(str(m.get("content", "")) for m in val_item.get("messages", []))
            v_shingles = extract_shingles(val_text)
            for i, t_shingles in train_shingles:
                sim = jaccard_similarity(t_shingles, v_shingles)
                if sim >= self.threshold:
                    leakage_errors.append(
                        f"Leakage detected: Val item {j} is a near-duplicate of Train item {i} (similarity={sim:.2f} >= {self.threshold})"
                    )
                    break
        return leakage_errors