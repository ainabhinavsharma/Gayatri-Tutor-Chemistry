"""Curriculum Structure Validator (Phase 11).

Validates curriculum graphs for structural integrity:
- Duplicate concept IDs
- Missing prerequisite IDs
- Prerequisite cycles (DAG validation)
- Orphan concepts
- Invalid difficulty levels or domains
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger("gayatri.curriculum.validator")

ALLOWED_DOMAINS = {"Thermodynamics", "Inorganic Chemistry", "General Chemistry"}


@dataclass
class CurriculumValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    concept_count: int = 0


class CurriculumValidator:
    """Validates structural integrity of curriculum definitions and prerequisite graphs."""

    def validate_concepts(self, concepts: List[dict]) -> CurriculumValidationResult:
        """Validate a list of concept dictionary definitions."""
        errors: List[str] = []
        warnings: List[str] = []

        if not concepts:
            return CurriculumValidationResult(is_valid=False, errors=["Curriculum concept list is empty."])

        concept_map: Dict[str, dict] = {}
        concept_ids: Set[str] = set()

        # 1. Check duplicate IDs and invalid attributes
        for idx, c in enumerate(concepts):
            cid = c.get("id") or c.get("concept_id")
            if not cid:
                errors.append(f"Concept at index {idx} is missing 'id'.")
                continue

            if cid in concept_ids:
                errors.append(f"Duplicate concept ID found: '{cid}'.")
            concept_ids.add(cid)
            concept_map[cid] = c

            diff = c.get("difficulty", 3)
            if not isinstance(diff, (int, float)) or not (1 <= diff <= 5):
                errors.append(f"Concept '{cid}' has invalid difficulty: {diff} (must be 1 to 5).")

            domain = c.get("domain", "")
            if domain and domain not in ALLOWED_DOMAINS:
                warnings.append(f"Concept '{cid}' has unlisted domain '{domain}'.")

        # 2. Check missing prerequisites
        adj: Dict[str, List[str]] = {cid: [] for cid in concept_ids}
        for cid, c in concept_map.items():
            prereqs = c.get("prerequisites") or []
            for p_id in prereqs:
                if p_id not in concept_ids:
                    errors.append(f"Concept '{cid}' references missing prerequisite ID '{p_id}'.")
                else:
                    adj[cid].append(p_id)

        # 3. Check cycle detection in prerequisite graph (DFS)
        visited: Dict[str, int] = {cid: 0 for cid in concept_ids}  # 0: unvisited, 1: visiting, 2: visited

        def dfs_cycle(node: str, path: List[str]) -> bool:
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

        for cid in concept_ids:
            if visited[cid] == 0:
                dfs_cycle(cid, [cid])

        # 4. Check orphan concepts (concepts with no prerequisites that are never referenced by any other concept)
        referenced: Set[str] = set()
        for neighbors in adj.values():
            referenced.update(neighbors)

        for cid, c in concept_map.items():
            prereqs = c.get("prerequisites") or []
            if not prereqs and cid not in referenced and len(concept_ids) > 1:
                warnings.append(f"Orphan concept detected: '{cid}' has no prerequisites and is not a prerequisite for any other concept.")

        is_valid = len(errors) == 0
        return CurriculumValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            concept_count=len(concept_ids),
        )
