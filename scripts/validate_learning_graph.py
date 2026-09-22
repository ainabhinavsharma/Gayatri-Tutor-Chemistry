#!/usr/bin/env python3
"""Gayatri AI — Learning Dependency Graph Validation Script (Section 23).

Validates the curriculum DAG:
1. Missing nodes (prerequisites referencing non-existent concepts)
2. Circular dependencies (cycles detected via DFS topological sort)
3. Orphan concepts (unconnected non-root nodes)
4. Invalid concept IDs / schema errors
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def validate_learning_graph(
    concepts_file: Path | None = None,
    prereqs_file: Path | None = None,
) -> bool:
    print("=" * 65)
    print("GAYATRI CHEMISTRY TUTOR — LEARNING GRAPH VALIDATION (Section 23)")
    print("=" * 65)

    graph_dir = root / "PRIVATE_WORK" / "learning_graph"
    c_file = concepts_file or (graph_dir / "concepts.json")
    p_file = prereqs_file or (graph_dir / "prerequisites.json")

    if not c_file.exists() or not p_file.exists():
        print(f"ERROR: Missing graph definitions in {graph_dir}")
        return False

    with open(c_file, encoding="utf-8") as f:
        c_data = json.load(f)
    with open(p_file, encoding="utf-8") as f:
        p_data = json.load(f)

    concepts = {item["id"]: item for item in c_data.get("concepts", [])}
    print(f"Concepts defined:     {len(concepts)}")

    # 1. Build adjacency list and check missing nodes
    adj = {cid: [] for cid in concepts}
    reverse_adj = {cid: [] for cid in concepts}
    missing_refs = []

    for dep in p_data.get("dependencies", []):
        cid = dep.get("concept_id")
        if cid not in concepts:
            missing_refs.append(f"Prerequisite entry for non-existent concept: '{cid}'")
            continue

        for prereq in dep.get("prerequisites", []):
            if prereq not in concepts:
                missing_refs.append(f"Concept '{cid}' references unknown prerequisite: '{prereq}'")
            else:
                adj[prereq].append(cid)  # prereq -> concept
                reverse_adj[cid].append(prereq)

    # 2. Detect cycles (DFS 3-color algorithm)
    # 0 = unvisited (white), 1 = visiting (gray), 2 = visited (black)
    color = {cid: 0 for cid in concepts}
    cycle_nodes = []

    def dfs_cycle(node, path):
        color[node] = 1
        path.append(node)
        for neighbor in adj[node]:
            if color[neighbor] == 1:
                # Cycle found!
                cycle_start = path.index(neighbor)
                cycle_nodes.append(" -> ".join(path[cycle_start:] + [neighbor]))
            elif color[neighbor] == 0:
                dfs_cycle(neighbor, path)
        path.pop()
        color[node] = 2

    for cid in concepts:
        if color[cid] == 0:
            dfs_cycle(cid, [])

    # 3. Detect orphan concepts (non-root nodes with 0 prerequisites and 0 dependents)
    orphans = []
    root_concepts = []
    for cid in concepts:
        num_prereqs = len(reverse_adj[cid])
        num_dependents = len(adj[cid])
        if num_prereqs == 0 and num_dependents == 0:
            orphans.append(cid)
        elif num_prereqs == 0:
            root_concepts.append(cid)

    # Report results
    all_passed = True

    print(f"Root concepts:        {len(root_concepts)} ({', '.join(root_concepts)})")
    print(f"Total dependencies:   {sum(len(v) for v in reverse_adj.values())}")

    print("\nVerification Checks:")
    # Check 1: Missing references
    if missing_refs:
        print(f"  - Node references:  FAIL ({len(missing_refs)} errors)")
        for err in missing_refs:
            print(f"      * {err}")
        all_passed = False
    else:
        print(f"  - Node references:  PASS (all prerequisite references exist)")

    # Check 2: Cycle detection
    if cycle_nodes:
        print(f"  - Cycle detection:  FAIL (circular dependency detected)")
        for c in cycle_nodes:
            print(f"      * Cycle: {c}")
        all_passed = False
    else:
        print(f"  - Cycle detection:  PASS (strict Directed Acyclic Graph - DAG)")

    # Check 3: Orphans
    if orphans:
        print(f"  - Orphan detection: WARNING ({len(orphans)} isolated concepts)")
        for o in orphans:
            print(f"      * Orphan: {o}")
    else:
        print(f"  - Orphan detection: PASS (zero disconnected concepts)")

    # Write validation summary to PRIVATE_WORK/learning_graph/graph_validation.json
    validation_summary = {
        "status": "PASS" if all_passed else "FAIL",
        "concepts_count": len(concepts),
        "dependency_count": sum(len(v) for v in reverse_adj.values()),
        "root_concepts": root_concepts,
        "cycles": cycle_nodes,
        "missing_references": missing_refs,
        "orphans": orphans,
    }
    summary_file = graph_dir / "graph_validation.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)

    print("\n" + "=" * 65)
    status_str = "PASS — Learning Dependency Graph is valid and acyclic" if all_passed else "FAIL — Graph issues detected"
    print(f"OVERALL STATUS:       {status_str}")
    print("=" * 65)
    return all_passed


if __name__ == "__main__":
    success = validate_learning_graph()
    sys.exit(0 if success else 1)
