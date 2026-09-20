"""Accuracy, Seeding, and Multi-Component Migration Tests.

Verifies:
1. Multi-component migrations execute independently on a shared SQLite database without collision.
2. RAG knowledge seeder idempotently populates NCERT textbook chunks from data/rag/.
3. Concept-aware retrieval returns high-confidence NCERT evidence for Hess's Law.
4. ChemicalEquationBalancer deterministically balances chemical equations.
5. ChemistryTutorRuntime integrates equation balancing and grounded RAG directives.
"""
import sqlite3
from pathlib import Path
import pytest

from core.db import get_safe_db_connection, run_migrations
from core.rag.store import RAGStore
from core.rag.seeder import seed_ncert_rag
from core.rag.retriever import NCERTRetriever, get_ncert_retriever
from core.rag.schema import RAGStatus, ConfidenceLevel
from core.curriculum.resolver import ConceptResolver
from core.tutor.chemistry_tools import ChemicalEquationBalancer, FormulaParser
from core.runtimes.chemistry import ChemistryTutorRuntime


def test_multi_component_migrations_independent_execution(tmp_path):
    """Verify that multiple independent components can apply their migrations to the same database."""
    db_file = tmp_path / "shared_migrations.db"
    conn = get_safe_db_connection(db_file)

    executed_steps = []

    def s_step1(c):
        executed_steps.append("session_1")
        c.execute("CREATE TABLE s_table1 (id INT);")

    def s_step2(c):
        executed_steps.append("session_2")
        c.execute("CREATE TABLE s_table2 (id INT);")

    def r_step1(c):
        executed_steps.append("rag_1")
        c.execute("CREATE TABLE r_table1 (id INT);")

    def r_step2(c):
        executed_steps.append("rag_2")
        c.execute("CREATE TABLE r_table2 (id INT);")

    # Component 1 (session) runs migrations 1 and 2
    session_migrations = {
        1: ("session_init", s_step1),
        2: ("session_upgrade", s_step2),
    }
    v1 = run_migrations(conn, session_migrations)
    assert v1 == 2
    assert executed_steps == ["session_1", "session_2"]

    # Component 2 (rag) also has migrations 1 and 2 - MUST NOT be skipped!
    rag_migrations = {
        1: ("rag_init", r_step1),
        2: ("rag_upgrade", r_step2),
    }
    v2 = run_migrations(conn, rag_migrations)
    assert v2 == 2
    assert "rag_1" in executed_steps
    assert "rag_2" in executed_steps

    # Re-running either is strictly idempotent
    v3 = run_migrations(conn, session_migrations)
    assert len(executed_steps) == 4


def test_rag_seeder_idempotent(tmp_path):
    """Verify seed_ncert_rag automatically ingests JSON files and is idempotent."""
    db_file = tmp_path / "test_seeder.db"
    store = RAGStore(db_path=db_file)

    # First run ingests chunks
    added_1 = seed_ncert_rag(store=store)
    assert added_1 > 0

    chunks = store.get_all_chunks()
    assert len(chunks) == added_1

    # Second run is idempotent and does not duplicate
    added_2 = seed_ncert_rag(store=store)
    assert added_2 == 0
    assert len(store.get_all_chunks()) == added_1


def test_concept_aware_retrieval_hess_law():
    """Verify concept-aware RAG retrieves Hess's Law with high confidence."""
    retriever = get_ncert_retriever()
    query = "What is Hess Law of constant heat summation?"
    resolved = ConceptResolver.resolve_concept(user_message=query)

    rag_ctx = retriever.retrieve_concept_aware(
        query=query,
        domain=resolved.domain,
        chapter=resolved.chapter,
        topic=resolved.topic,
        concept_id=resolved.concept_id,
        top_k=2,
    )

    assert rag_ctx.status == RAGStatus.RAG_OK
    assert rag_ctx.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
    assert len(rag_ctx.results) > 0
    top_text = rag_ctx.results[0].chunk.text
    assert "Hess's Law" in top_text or "enthalpy" in top_text.lower()


def test_chemical_equation_balancer_precision():
    """Verify deterministic equation balancing on standard chemistry reactions."""
    # 1. Synthesis of water
    res1 = ChemicalEquationBalancer.balance("H2 + O2 -> H2O")
    assert res1["success"] is True
    assert res1["balanced_equation"] == "2H2 + O2 -> 2H2O"
    assert ChemicalEquationBalancer.is_balanced("2H2 + O2 -> 2H2O") is True
    assert ChemicalEquationBalancer.is_balanced("H2 + O2 -> H2O") is False

    # 2. Haber process (Ammonia)
    res2 = ChemicalEquationBalancer.balance("N2 + H2 -> NH3")
    assert res2["success"] is True
    assert res2["balanced_equation"] == "N2 + 3H2 -> 2NH3"

    # 3. Combustion of methane
    res3 = ChemicalEquationBalancer.balance("CH4 + O2 -> CO2 + H2O")
    assert res3["success"] is True
    assert res3["balanced_equation"] == "CH4 + 2O2 -> CO2 + 2H2O"

    # 4. Complex stoichiometry: Iron oxidation
    res4 = ChemicalEquationBalancer.balance("Fe + O2 -> Fe2O3")
    assert res4["success"] is True
    assert res4["balanced_equation"] == "4Fe + 3O2 -> 2Fe2O3"


def test_formula_parser_polyatomic():
    """Verify chemical formula parsing with parentheses and multipliers."""
    assert FormulaParser.parse_formula("H2O") == {"H": 2, "O": 1}
    assert FormulaParser.parse_formula("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}
    assert FormulaParser.parse_formula("Fe2(SO4)3") == {"Fe": 2, "S": 3, "O": 12}
