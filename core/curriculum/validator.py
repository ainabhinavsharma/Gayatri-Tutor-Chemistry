"""Curriculum Structure Validator (Phase 12 / Section 18).

Validates curriculum graphs for structural integrity:
- Unique concept IDs
- Valid prerequisite IDs (stable programmatic identifiers, rejecting free text)
- No cycles (strict DAG validation)
- No orphan prerequisites (prerequisites pointing to non-existent concepts)
- Valid domains and difficulty levels (1..5 or normalized 0.0..1.0)
- Learning outcomes and question mappings
- CI fail-fast enforcement via CurriculumCorruptionError and validate_or_raise()
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("gayatri.curriculum.validator")

ALLOWED_DOMAINS = {
    "Thermodynamics",
    "Inorganic Chemistry",
    "General Chemistry",
    "Organic Chemistry",
    "Physical Chemistry",
}

STABLE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.\-]+$")


class CurriculumCorruptionError(Exception):
    """Raised when curriculum data fails structural integrity or validation rules."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass
class CurriculumValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    concept_count: int = 0


class CurriculumValidator:
    """Validates structural integrity of curriculum definitions and prerequisite graphs (Section 18)."""

    def validate_concepts(self, concepts: list[dict]) -> CurriculumValidationResult:
        """Validate a list of concept dictionary definitions."""
        errors: list[str] = []
        warnings: list[str] = []

        if not concepts:
            return CurriculumValidationResult(is_valid=False, errors=["Curriculum concept list is empty."])

        concept_map: dict[str, dict] = {}
        concept_ids: set[str] = set()

        # 1. Check unique concept IDs, stable ID formatting, and valid attributes
        for idx, c in enumerate(concepts):
            cid = c.get("id") or c.get("concept_id")
            if not cid:
                errors.append(f"Concept at index {idx} is missing 'id'.")
                continue

            if not isinstance(cid, str) or not STABLE_ID_PATTERN.match(cid):
                errors.append(
                    f"Concept ID '{cid}' is not a valid stable identifier (must be alphanumeric, dots, hyphens, underscores without spaces)."
                )

            if cid in concept_ids:
                errors.append(f"Duplicate concept ID found: '{cid}'.")
            concept_ids.add(cid)
            concept_map[cid] = c

            # Difficulty validation: accept 1..5 or normalized 0.0..1.0
            diff = c.get("difficulty", 3)
            if not isinstance(diff, (int, float)) or not (1 <= diff <= 5 or 0.0 <= diff <= 1.0):
                errors.append(
                    f"Concept '{cid}' has invalid difficulty: {diff} (must be 1 to 5 or normalized 0.0 to 1.0)."
                )

            # Domain validation
            domain = c.get("domain", "")
            if domain and domain not in ALLOWED_DOMAINS:
                warnings.append(f"Concept '{cid}' has unlisted domain '{domain}'.")

            # Learning outcomes validation
            outcomes = c.get("learning_outcomes") or c.get("description")
            if not outcomes:
                warnings.append(f"Concept '{cid}' is missing learning outcomes or description.")

            # Question mappings validation
            q_mappings = c.get("questions") or c.get("assessment_types") or c.get("question_ids")
            if not q_mappings:
                warnings.append(f"Concept '{cid}' has no question mappings or assessment types defined.")

        # 2. Check prerequisite IDs: existence, stable ID format, orphan prerequisites, self-dependency
        adj: dict[str, list[str]] = {cid: [] for cid in concept_ids}
        for cid, c in concept_map.items():
            prereqs = c.get("prerequisites") or []
            for p_id in prereqs:
                if not isinstance(p_id, str) or not STABLE_ID_PATTERN.match(p_id):
                    errors.append(
                        f"Concept '{cid}' references unstable/free-text prerequisite '{p_id}'. Stable identifier required (e.g. 'chem.atomic_structure')."
                    )
                    continue

                if p_id == cid:
                    errors.append(f"Concept '{cid}' cannot have itself as a prerequisite.")
                    continue

                if p_id not in concept_ids:
                    errors.append(f"Concept '{cid}' references missing prerequisite ID '{p_id}'.")
                else:
                    adj[cid].append(p_id)

        # 3. Check cycle detection in prerequisite graph (strict DAG validation via DFS)
        visited: dict[str, int] = {cid: 0 for cid in concept_ids}  # 0: unvisited, 1: visiting, 2: visited

        def dfs_cycle(node: str, path: list[str]) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                if visited[neighbor] == 1:
                    cycle_str = " -> ".join(path + [neighbor])
                    errors.append(f"Prerequisite cycle detected: {cycle_str}")
                    return True
                if visited[neighbor] == 0:
                    if dfs_cycle(neighbor, path + [neighbor]):
                        return True
            visited[node] = 2
            return False

        for cid in sorted(concept_ids):
            if visited[cid] == 0:
                dfs_cycle(cid, [cid])

        # 4. Check orphan concepts (no prerequisites and never referenced by any other concept)
        referenced: set[str] = set()
        for neighbors in adj.values():
            referenced.update(neighbors)

        for cid, c in concept_map.items():
            prereqs = c.get("prerequisites") or []
            if not prereqs and cid not in referenced and len(concept_ids) > 1:
                warnings.append(
                    f"Orphan concept detected: '{cid}' has no prerequisites and is not a prerequisite for any other concept."
                )

        is_valid = len(errors) == 0
        return CurriculumValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            concept_count=len(concept_ids),
        )

    def validate_curriculum_file(self, file_path: str | Path) -> CurriculumValidationResult:
        """Load a curriculum JSON file and validate its concept graph."""
        p = Path(file_path)
        if not p.exists():
            return CurriculumValidationResult(is_valid=False, errors=[f"Curriculum file not found: {p}"])

        try:
            with open(p, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            return CurriculumValidationResult(is_valid=False, errors=[f"JSON decoding error in {p}: {e}"])

        if "concepts" in data:
            return self.validate_concepts(data["concepts"])
        elif "domains" in data:
            return self.validate_manifest(data)
        else:
            return CurriculumValidationResult(
                is_valid=False,
                errors=[f"Curriculum file {p} does not contain 'concepts' or 'domains' key."],
            )

    def validate_manifest(self, manifest: Any) -> CurriculumValidationResult:
        """Validate a curriculum manifest structure containing domains."""
        domains = manifest.get("domains", []) if isinstance(manifest, dict) else getattr(manifest, "domains", [])
        if not domains:
            return CurriculumValidationResult(is_valid=False, errors=["Manifest contains no domains."])

        all_concepts: list[dict] = []
        for d in domains:
            domain_name = d.get("name", "") if isinstance(d, dict) else getattr(d, "name", "")
            topics = d.get("topics", []) if isinstance(d, dict) else getattr(d, "topics", [])
            subtopics = d.get("subtopics", []) if isinstance(d, dict) else getattr(d, "subtopics", [])
            outcomes = d.get("learning_outcomes", []) if isinstance(d, dict) else getattr(d, "learning_outcomes", [])
            prereqs = d.get("prerequisites", []) if isinstance(d, dict) else getattr(d, "prerequisites", [])

            # Generate synthetic concept dicts for domain topics
            domain_id = domain_name.lower().replace(" ", "_").replace("-", "_")
            for idx, t in enumerate(topics):
                tid = t.lower().replace(" ", "_").replace(",", "").replace("'", "").replace("-", "_")
                all_concepts.append({
                    "id": tid,
                    "name": t,
                    "domain": domain_name,
                    "difficulty": 3,
                    "description": subtopics[idx] if idx < len(subtopics) else "",
                    "learning_outcomes": outcomes,
                    "prerequisites": [],
                    "assessment_types": ["conceptual"],
                })

        return self.validate_concepts(all_concepts)

    def validate_or_raise(self, concepts_or_path: Any) -> CurriculumValidationResult:
        """Validate concepts, file, or manifest; raise CurriculumCorruptionError on failure (CI fail-fast)."""
        if isinstance(concepts_or_path, (str, Path)):
            result = self.validate_curriculum_file(concepts_or_path)
        elif isinstance(concepts_or_path, list):
            result = self.validate_concepts(concepts_or_path)
        elif isinstance(concepts_or_path, dict) and "concepts" in concepts_or_path:
            result = self.validate_concepts(concepts_or_path["concepts"])
        elif isinstance(concepts_or_path, dict) and "domains" in concepts_or_path:
            result = self.validate_manifest(concepts_or_path)
        else:
            result = self.validate_manifest(concepts_or_path)

        if not result.is_valid:
            error_msg = f"Curriculum corruption detected ({len(result.errors)} errors):\n" + "\n".join(
                f" - {err}" for err in result.errors
            )
            raise CurriculumCorruptionError(error_msg, errors=result.errors)

        return result
