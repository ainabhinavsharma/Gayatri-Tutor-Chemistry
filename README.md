# Gayatri Chemistry Tutor --- Adaptive AI Learning Platform

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Build & Tests](https://img.shields.io/badge/tests-305%20passed-brightgreen.svg)]()

**Gayatri Chemistry Tutor** is an evidence-driven, NCERT-aligned adaptive AI tutoring system for High School & Entrance Exam Chemistry (specifically focused on **Thermodynamics** and **Inorganic Chemistry**).

Unlike generic LLM wrappers, Gayatri Tutor pairs a neural language model with a **deterministic adaptive learning engine**, persistent student mastery tracking, structured answer evaluation, concept-aware RAG, and isolated conversation states.

---

## Key Capabilities & Architecture

```text
             ┌─────────────────────────┐
             │                         │
             v                         │
       Student Evidence                │
             │                         │
             v                         │
      Answer Evaluation                │
             │                         │
             v                         │
       Learning Event                  │
             │                         │
             v                         │
      Student Mastery State            │
             │                         │
             v                         │
   Adaptive Policy / Scheduler         │
             │                         │
             v                         │
       Next Learning Action            │
             │                         │
             v                         │
        Tutor Response                 │
             │                         │
             └─────────────────────────┘
```

1. **Student-Scoped Learning State (`core/tutor/state.py`)**
   - Separate global curriculum definitions from student mastery (`student_concept_mastery`).
   - Append-only evidence logs (`learning_events`) with unique turn IDs (`turn_id`) and idempotency checks.
   - Complete isolation between students (Student A cannot access or mutate Student B data).
   - Strict separation between **General Assistant** conversation history and **Chemistry Tutor** mastery state.

2. **Structured Chemistry Answer Evaluator (`core/tutor/evaluator.py`)**
   - Zero keyword matching fallbacks (`["yes", "400"]` deleted).
   - Deterministic evaluators for MCQ, numeric tolerances (with unit checks), formula/reaction normalization.
   - Returns structured `EvaluationResult` with `correct`, `partially_correct`, `incorrect`, or `uncertain` confidence states.

3. **Adaptive Learning Engine (`core/learning/`)**
   - **Multi-factor Mastery Model (`mastery.py`)**: `mastery = 0.45*recent_acc + 0.25*long_term_acc + 0.15*diff_score + 0.10*independent_success + 0.05*retention_score`.
   - **Adaptive Difficulty Policy (`policy.py`)**: Dynamic difficulty level adjustment (1 to 5) based on independent recall and conceptual errors.
   - **Misconception Tracking (`misconceptions.py`)**: Controlled misconception codes for Thermodynamics & Inorganic Chemistry.
   - **Concept Selector (`selector.py`)**: Multi-factor candidate ranking considering prerequisite readiness, mastery gap, review urgency, and misconception risk.
   - **Spaced Review (`scheduler.py`)**: Configurable interval progression (1d -> 3d -> 7d -> 14d -> 30d) with delayed recall retention enforcement.
   - **Progress Service (`progress.py`)**: Single authoritative progress API computing domain/concept analytics.

4. **Assessment Engine (`core/assessment/manager.py`)**
   - Question bank schema, assessment session management, attempt recording, anti-leakage question sanitization, and score computation.

5. **NCERT Concept-Aware RAG (`core/rag/`)**
   - Enriches retrieval queries with active curriculum context.
   - Priority ranking: `NCERT` > `TRUSTED_CURRICULUM` > `FALLBACK`.
   - Observable RAG status (`RAG_STATUS_OK`, `RAG_STATUS_EMPTY`, `RAG_STATUS_ERROR`).

6. **Reliability & Crash Recovery (`core/tutor/lifecycle.py`)**
   - Step-by-step turn lifecycle persistence (`TURN_STARTED` -> ... -> `TURN_COMMITTED`).
   - Automatic startup recovery for interrupted turns.

7. **Model & Configuration Consistency (`model_manifest.json` & `core/model_fetch/manifest_validator.py`)**
   - Declarative model manifest file ensuring consistent local model loading and quantization details.

---

## Core Scope

- **Primary Curriculum Domains:**
  - **Thermodynamics:** Enthalpy, First Law, Hess's Law, Entropy, Gibbs Free Energy, Heat Capacities ($C_p, C_v$), Work conventions.
  - **Inorganic Chemistry:** Periodic Trends, Atomic Structure, Coordination Compounds, Oxidation States, Redox Reactions, Metallurgy.

---

## Socratic SLM Architecture (v3.0.1)

The application utilizes an ultra-lean, specialized 0.5B Small Language Model:
- **Base Architecture:** `Qwen/Qwen2.5-0.5B-Instruct`
- **Model Format:** GGUF `Q4_K_M` (~379 MB)
- **Local Inference:** Native `llama.cpp` (CPU-optimized, zero GPU required)
- **Fine-Tuning:** 2,500 curated Socratic dialogues spanning 5 pedagogical pillars (Persona, Explain, Question, Evaluate, Remediate)
- **Context Profile:** Bounded 3-turn history with compact atomic RAG evidence cards (<75 tokens) for sub-second CPU generation and minimal memory consumption (<800 MB RAM).

---

## Installation & Setup

### Prerequisites

- Python 3.12+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/ainabhinavsharma/Gayatri-Tutor-Chemistry.git
cd Gayatri-Tutor-Chemistry

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Running Tests

Execute the full regression suite:

```bash
pytest
```

Run specific phase test suites:

```bash
pytest tests/test_phase1_learning_state.py
pytest tests/test_phase2_evaluator.py
pytest tests/test_phase3_concept_resolution.py
pytest tests/test_phase4_adaptive_engine.py
pytest tests/test_phase5_spaced_review.py
pytest tests/test_phase6_assessment_engine.py
pytest tests/test_phase7_rag.py
pytest tests/test_phase8_state_machine.py
pytest tests/test_phase9_progress.py
pytest tests/test_phase10_reliability.py
pytest tests/test_phase11_curriculum_validation.py
pytest tests/test_phase12_security.py
pytest tests/test_phase13_model_config.py
```

---

## Verification & Status

All 14 Execution Plan phases and v4 engineering upgrades have been fully implemented, verified, and integrated with **305 passed unit and integration tests**.

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Baseline & Discovery | `DONE` |
| Phase 1 | Student-Scoped Learning State & Two-Mode Architecture | `DONE` |
| Phase 2 | Chemistry Answer Evaluator & Bonding Domain Expansion | `DONE` |
| Phase 3 | Dynamic Concept Resolution | `DONE` |
| Phase 4 | Adaptive Learning Engine | `DONE` |
| Phase 5 | Spaced Review & Retention Queue | `DONE` |
| Phase 6 | Interactive Assessment Engine & UI Runner | `DONE` |
| Phase 7 | NCERT Concept-Aware RAG | `DONE` |
| Phase 8 | Tutor State Machine Integration | `DONE` |
| Phase 9 | Progress & Analytics Service & JSON Export | `DONE` |
| Phase 10 | Reliability & Crash Recovery | `DONE` |
| Phase 11 | Curriculum Validation | `DONE` |
| Phase 12 | Security & Student Isolation | `DONE` |
| Phase 13 | Model Manifest & Config | `DONE` |
| Phase 14 | Documentation & Production Cleanup | `DONE` |

---

## License

This project is licensed under the MIT License.
