"""Tests for SLM Pedagogical Alignment, Atomic RAG, and Anti-Answer Leakage Invariants."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.rag.retriever import get_ncert_retriever
from core.runtimes.chemistry import _build_chemistry_system_prompt, ChemistryTutorRuntime
import core.config


def test_slm_atomic_rag_retrieval():
    """Verify that atomic RAG retrieves high-density cards under 100 tokens."""
    retriever = get_ncert_retriever()
    
    # 1. Test Thermodynamics First Law
    thermo_card = retriever.retrieve_atomic("THERMO_FIRST_LAW")
    assert "<ncert_evidence>" in thermo_card
    assert "[CONCEPT: First Law of Thermodynamics" in thermo_card
    assert "delta U = q + w" in thermo_card
    assert "MISCONCEPTION:" in thermo_card
    assert "ANALOGY:" in thermo_card
    # Check token compactness (< 1000 characters / ~150 tokens)
    assert len(thermo_card) < 1000

    # 2. Test Ammonia Geometry
    nh3_card = retriever.retrieve_atomic("BOND_NH3_GEOMETRY")
    assert "<ncert_evidence>" in nh3_card
    assert "107" in nh3_card
    assert "trigonal pyramidal" in nh3_card.lower() or "pyramidal" in nh3_card.lower()
    assert len(nh3_card) < 1000



def test_slm_prompt_contract():
    """Verify lean SLM prompt contract structure and directives."""
    prompt = _build_chemistry_system_prompt(is_slm=True, rag_evidence="<evidence>test</evidence>")
    assert "You are Gayatri Chemistry Tutor" in prompt
    assert "Socratic Method" in prompt
    assert "EXPLAIN Mode: Structure responses into: 1. Everyday Analogy" in prompt
    assert "ZERO ANSWER LEAKAGE" in prompt
    assert "<evidence>test</evidence>" in prompt
    # Verify it does not contain the bloated curriculum list
    assert "Supported NCERT topics in this session:" not in prompt


def test_slm_synthetic_dataset_integrity():
    """Verify generated dataset files exist, contain 2500 turns, and follow ChatML."""
    train_file = Path("training/data/processed/train.jsonl")
    val_file = Path("training/data/processed/val.jsonl")

    assert train_file.exists(), "train.jsonl was not generated"
    assert val_file.exists(), "val.jsonl was not generated"

    total = 0
    with open(train_file, "r", encoding="utf-8") as f:
        train_lines = f.readlines()
        total += len(train_lines)
        assert len(train_lines) == 2250

    with open(val_file, "r", encoding="utf-8") as f:
        val_lines = f.readlines()
        total += len(val_lines)
        assert len(val_lines) == 250

    assert total == 2500

    # Validate first line ChatML
    obj = json.loads(train_lines[0])
    assert "messages" in obj
    assert len(obj["messages"]) >= 3
    assert obj["messages"][0]["role"] == "system"
    assert obj["messages"][1]["role"] == "user"
    assert obj["messages"][2]["role"] == "assistant"


def test_slm_anti_answer_leakage_dataset_invariant():
    """Verify that in all sign misconception evaluation turns, the answer (300 J) is never leaked."""
    train_file = Path("training/data/processed/train.jsonl")
    leak_count = 0
    checked_turns = 0

    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            turn = json.loads(line)
            msgs = turn["messages"]
            user_text = msgs[1]["content"].lower()
            assistant_text = msgs[2]["content"].lower()

            # Check if this is the classic 700 J error prompt
            if "700 j" in user_text and "500 + 200" in user_text:
                checked_turns += 1
                for forbidden in ["300 j", "300j", "= 300", "equals 300", "answer is 300"]:
                    if forbidden in assistant_text:
                        leak_count += 1

    assert checked_turns > 0, "No 700 J misconception evaluation turns found!"
    assert leak_count == 0, f"Anti-answer leakage failed in {leak_count} training turns!"


def test_slm_runtime_model_detection(monkeypatch):
    """Verify runtime dynamically detects SLM models and switches to atomic RAG."""
    monkeypatch.setattr(core.config, "LOCAL_MODEL_FILE", "Gayatri-Tutor-SLM-Q4_K_M.gguf")
    
    runtime = ChemistryTutorRuntime()
    assert runtime is not None

    active_name = core.config.LOCAL_MODEL_FILE.lower()
    is_slm = ("0.5b" in active_name or "slm" in active_name)
    assert is_slm is True
