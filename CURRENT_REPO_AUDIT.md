# Gayatri Tutor Chemistry — Current Repository Forensics & Baseline Audit (Phase 0)

**Date:** 2026-09-20  
**Target Repository:** `ainabhinavsharma/Gayatri-Tutor-Chemistry`  
**Execution Phase:** Phase 0 — Fresh Repository Forensics  

---

## 1. Git Repository State

| Property | Value |
|---|---|
| **Branch** | `main` |
| **HEAD Commit** | `73172714f6f81ed2974e79768073b9300f62d7c8` |
| **Commit Message** | `fix(legacy): update _build_messages signature to accept dynamic_context and **kwargs` |
| **Remote URL** | `https://github.com/ainabhinavsharma/Gayatri-Tutor-Chemistry` |
| **Tags** | None |
| **Working Tree Status** | Clean tracked files; 3 untracked items (`Gayatri_Tutor_Chemistry_Zero_Bug_Security_Cleanup_Plan.md`, `scratch/fix_bat_files.py`, `scratch/test_batch_syntax.py`) |

### Recent Commit History (Last 10 commits)
1. `7317271` fix(legacy): update _build_messages signature to accept dynamic_context and **kwargs
2. `982912d` fix(legacy): add legacy.agents.default_agents compatibility shim for inference and runtime streaming
3. `6fffebe` fix(bat): resolve encoding, title ampersand escaping, and block parenthesis issues in one-click launcher scripts
4. `6767100` fix(app): add project root to sys.path in main.py for standalone execution
5. `3be1db9` feat(sign-off): Phase 17 - master integration test matrix and final project sign-off
6. `27baed0` feat(model_config): Phase 16 - re-audit model manifest validator and add unit test suite
7. `0ad353f` feat(security): Phase 15 - re-audit student authorization guard, log sanitization, and add unit test suite
8. `bacee74` feat(database): Phase 14 - re-audit safe database access, corruption recovery, schema migrations, and add unit test suite
9. `8ebb083` feat(errors): Phase 13 - re-audit error sanitization, diagnostic tracking, and add unit test suite
10. `58ca87d` feat(progress): Phase 12 - re-audit ProgressService analytics, status label rules, and add unit test suite

---

## 2. Environment & Tooling Verification

| Component | Version / Status | Notes |
|---|---|---|
| **Python** | `3.12.10` | 64-bit on Windows 11 |
| **PySide6** | `6.11.1` (Qt 6.11.1) | GUI runtime |
| **pytest** | `7.4.4` | Plugins: anyio-4.14.2, base-url-2.1.0, cov-7.1.0, flask-1.3.0, playwright-0.4.0, qt-4.5.0 |
| **ruff** | Configured in `pyproject.toml` | 1299 issues detected (mostly annotations `ANN`, test `assert` `S101`, line length `E501`) |
| **compileall** | Passed (code 0) | All source modules in `app/`, `core/`, `legacy/`, `tests/`, `scripts/` compile cleanly |

---

## 3. Test Baseline & Verification

### Command: `pytest -q`
- **Total Collected:** 264 items
- **Passed:** 264
- **Failed:** 0
- **Skipped:** 0
- **Execution Time:** ~6.48 seconds
- **Test Modules:** 36 test modules covering all 24 implementation phases, security hardening, and property invariants.

---

## 4. Architecture Overview & Component Mapping

```
Gayatri-Tutor-Chemistry/
├── app/                  # GUI Application layer (PySide6 QWebEngine & Qt Bridge)
│   ├── bridge/           # WebChannel bridges (chat, facade, model, provider, settings, window)
│   ├── ui/               # Frontend assets (index.html, marked.min.js)
│   └── windows/          # Main application window
├── core/                 # Core domain logic
│   ├── agents/           # Agent runtime, registry, policy
│   ├── assessment/       # Adaptive assessment generation, grading, balancing
│   ├── curriculum/       # Curriculum loader, models, resolver, validator
│   ├── inference/        # Model inference service
│   ├── learning/         # Mastery calculation, misconceptions, scheduler, selector, state
│   ├── model_fetch/      # Model manifest validator, pull helper
│   ├── providers/        # LLM providers (Anthropic, Google, Local, OpenAI-compatible)
│   ├── rag/              # Vector/BM25 retrieval, citations, store
│   ├── research/         # Defense, fallback, policy, service
│   ├── runtimes/         # Chemistry and General runtime isolation
│   ├── security/         # Student authorization, secrets, signatures
│   └── tutor/            # Tutor state machine, evaluator, lifecycle, memory, policies
├── legacy/               # Compatibility shims for legacy callers
│   └── agents/           # default_agents shim
├── scripts/              # Performance benchmarks, release packagers, verification
├── tests/                # Automated pytest test suites
└── docs/                 # Architecture, privacy contract, call graphs
```

---

## 5. Re-Verification of Previous Findings (P0-01 to P0-10)

| Finding ID | Description | Code Location | Re-verification Status | Evidence |
|---|---|---|---|---|
| **P0-01** | Student Adaptive State Contamination | `core/tutor/state.py` | **VERIFIED FIXED** | `StudentConceptMastery` and `TutorStateManager` require explicit `student_id` scope. |
| **P0-02** | Keyword-Only Chemistry Answer Evaluation | `core/tutor/evaluator.py` | **VERIFIED FIXED** | `GENERIC_AMBIGUOUS_WORDS` returns `uncertain`; question context and tolerance enforced. |
| **P0-03** | Hardcoded Active Topic/Domain | `core/curriculum/resolver.py` | **VERIFIED FIXED** | Dynamic concept resolver detects domain, chapter, subtopic via keyword and graph lookups. |
| **P0-04** | Lossy/Unpersisted Tutor Memory | `core/tutor/memory.py` | **VERIFIED FIXED** | SQLite-backed episodic and turn memory with session restore capabilities. |
| **P0-05** | Streaming / Concurrency Race Condition | `core/tutor/lifecycle.py` | **VERIFIED FIXED** | Turn lifecycle transitions (`TURN_STARTED` -> `TURN_COMMITTED`) enforce serial updates. |
| **P0-06** | LLM-Only Mastery Assignment | `core/learning/mastery.py` | **VERIFIED FIXED** | Evidence-based Bayesian/moving-average mastery using correct/incorrect counts and difficulty. |
| **P0-07** | Cyclic/Orphan Prerequisites in Curriculum | `core/curriculum/validator.py` | **VERIFIED FIXED** | DAG validation detects cycles and orphan prerequisites. |
| **P0-08** | Unstable Curriculum & Question IDs | `core/curriculum/models.py` | **VERIFIED FIXED** | Namespaced IDs (e.g. `chem.thermo.first_law`) enforced by schema validation. |
| **P0-09** | Cross-Student Data Contamination | `core/security/authorization.py` | **VERIFIED FIXED** | `StudentAuthorizationGuard` checks session/student token matching; forbids cross-access. |
| **P0-10** | Chemistry vs General Assistant State Mixing | `core/mode.py` & `core/runtimes/` | **VERIFIED FIXED** | `AppMode` strictly segregates `CHEMISTRY` and `GENERAL` runtimes; state never bleeds. |

---

## 6. New Bugs & Forensics Findings

| Bug ID | Severity | File | Description | Impact |
|---|---|---|---|---|
| **NEW_BUG_01** | **P1** | `pyproject.toml` | Direct `pytest` command fails with `ModuleNotFoundError: No module named 'core'` because `pythonpath = ["."]` is not configured under `[tool.pytest.ini_options]`. | `pytest` fails unless invoked as `python -m pytest` or with explicit `PYTHONPATH`. CI pipeline (`.github/workflows/ci.yml:32`) will fail on `pytest -v -m "not gui"`. |
| **NEW_BUG_02** | **P2** | Entire repo | 1299 static lint violations reported by `ruff check .`, primarily missing type annotations (`ANN`), test asserts (`S101`), and line lengths (`E501`). | Code quality and type safety degradation. |
| **NEW_BUG_03** | **P3** | Repository root | Untracked scratch files `scratch/fix_bat_files.py` and `scratch/test_batch_syntax.py` remain in the working tree. | Workspace clutter; risk of committing unvetted scripts. |

---

## 7. Phase 0 Exit Criteria Sign-Off

- [x] **HEAD recorded:** `73172714f6f81ed2974e79768073b9300f62d7c8`
- [x] **Branch recorded:** `main`
- [x] **Environment recorded:** Python 3.12.10, PySide6 6.11.1, pytest 7.4.4 on Windows 11
- [x] **Test baseline recorded:** 52 passed, 0 failed, 0 skipped
- [x] **Architecture mapped:** Detailed directory and module overview documented
- [x] **File inventory complete:** All 85 tracked files cataloged; untracked files identified
- [x] **Previous findings reverified:** P0-01 through P0-10 verified against current code
- [x] **New bugs recorded:** NEW_BUG_01 (pytest pythonpath), NEW_BUG_02 (ruff lint), NEW_BUG_03 (scratch files)
