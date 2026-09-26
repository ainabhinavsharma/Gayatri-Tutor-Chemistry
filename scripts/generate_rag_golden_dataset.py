"""Generate Golden RAG Retrieval Dataset (Phase 4).

Creates docs/datasets/rag_golden_dataset.json containing golden evaluation queries,
expected concept matches, required terms, and source citations.
"""
from __future__ import annotations

import json
from pathlib import Path

DATASET_PATH = Path("docs/datasets/rag_golden_dataset.json")

GOLDEN_QUERIES = [
    {
        "query_id": "RAG_001",
        "query": "What is the First Law of Thermodynamics and how is work defined?",
        "expected_concept": "THERMO_FIRST_LAW",
        "expected_chapter": "Unit 6",
        "expected_source": "NCERT Class 11 Chemistry Chapter 6",
        "required_terms": ["internal energy", "heat", "work", "delta U"],
    },
    {
        "query_id": "RAG_002",
        "query": "Define entropy and explain spontaneity in terms of Gibbs free energy",
        "expected_concept": "THERMO_ENTROPY",
        "expected_chapter": "Unit 6",
        "expected_source": "NCERT Class 11 Chemistry Chapter 6",
        "required_terms": ["entropy", "Gibbs", "spontaneous", "disorder"],
    },
    {
        "query_id": "RAG_003",
        "query": "What is Hess's law of constant heat summation?",
        "expected_concept": "THERMO_HESS_LAW",
        "expected_chapter": "Unit 6",
        "expected_source": "NCERT Class 11 Chemistry Chapter 6",
        "required_terms": ["enthalpy change", "summation", "path independent"],
    },
    {
        "query_id": "RAG_004",
        "query": "Why does ammonia NH3 have a trigonal pyramidal shape under VSEPR theory?",
        "expected_concept": "BOND_VSEPR",
        "expected_chapter": "Unit 4",
        "expected_source": "NCERT Class 11 Chemistry Chapter 4",
        "required_terms": ["lone pair", "bond pair", "pyramidal", "repulsion"],
    },
    {
        "query_id": "RAG_005",
        "query": "How does ionic radius change across isoelectronic species like O2-, F-, Na+, Mg2+?",
        "expected_concept": "PERIOD_IONIC_RADIUS",
        "expected_chapter": "Unit 3",
        "expected_source": "NCERT Class 11 Chemistry Chapter 3",
        "required_terms": ["effective nuclear charge", "isoelectronic", "ionic radius"],
    },
    {
        "query_id": "RAG_006",
        "query": "What is the difference between a monodentate and bidentate ligand in coordination chemistry?",
        "expected_concept": "COORD_LIGAND",
        "expected_chapter": "Unit 9",
        "expected_source": "NCERT Class 12 Chemistry Chapter 9",
        "required_terms": ["donor atom", "coordination", "chelating", "ligand"],
    },
    {
        "query_id": "RAG_007",
        "query": "How is work done calculated during gas expansion against constant external pressure?",
        "expected_concept": "THERMO_WORK",
        "expected_chapter": "Unit 6",
        "expected_source": "NCERT Class 11 Chemistry Chapter 6",
        "required_terms": ["expansion", "external pressure", "w = -P delta V"],
    },
    {
        "query_id": "RAG_008",
        "query": "What is the definition of standard enthalpy of formation?",
        "expected_concept": "THERMO_ENTHALPY",
        "expected_chapter": "Unit 6",
        "expected_source": "NCERT Class 11 Chemistry Chapter 6",
        "required_terms": ["standard state", "1 mole", "elements"],
    },
    {
        "query_id": "RAG_009",
        "query": "Explain hybridization of atomic orbitals in methane CH4",
        "expected_concept": "BOND_HYBRIDISATION",
        "expected_chapter": "Unit 4",
        "expected_source": "NCERT Class 11 Chemistry Chapter 4",
        "required_terms": ["sp3", "tetrahedral", "mixing of orbitals"],
    },
    {
        "query_id": "RAG_010",
        "query": "What is electronegativity and how does it trend in the periodic table?",
        "expected_concept": "PERIOD_ELECTRONEGATIVITY",
        "expected_chapter": "Unit 3",
        "expected_source": "NCERT Class 11 Chemistry Chapter 3",
        "required_terms": ["shared pair", "attract", "Paulings scale"],
    },
]


def main():
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    benchmark_data = {
        "version": "1.0.0",
        "description": "Gayatri AI Phase 4 Frozen Golden RAG Retrieval Evaluation Dataset",
        "total_queries": len(GOLDEN_QUERIES),
        "queries": GOLDEN_QUERIES,
    }

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"Successfully generated golden RAG retrieval dataset at {DATASET_PATH}")
    print(f"Total Golden Queries: {len(GOLDEN_QUERIES)}")


if __name__ == "__main__":
    main()
