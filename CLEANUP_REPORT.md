# Gayatri AI Chemistry Tutor — Repository Cleanup Report (Phase 25 / Sections 31–34)

**Audit & Cleanup Date:** 2026-09-21  
**Target Repository:** `ainabhinavsharma/Gayatri-Tutor-Chemistry`  
**Execution Phase:** Phase 25 — Cleanup  
**Compliance Standard:** Sections 31–34 of Zero-Bug, Silent-Failure, Security & Cleanup Plan  

---

## 1. Confirmed Runtime Files

The following files constitute the essential runtime architecture of the Gayatri AI Chemistry Tutor application. All have been verified through imports, test coverage, and execution:

### Application & GUI (`app/`)
- `app/__init__.py`: Package initialization.
- `app/main.py`: Main desktop application entry point (PySide6 Qt GUI).
- `app/install_hook.py`: Runtime dependency and environment verification hook.
- `app/windows/__init__.py`, `app/windows/main_window.py`: PySide6 QWebEngine desktop window with title bar and WebChannel bridge.
- `app/bridge/__init__.py`: Bridge package initialization.
- `app/bridge/facade.py`: Central facade coordinating all capability bridges with the core orchestrator.
- `app/bridge/chat.py`: QWebChannel bridge for chat messaging, streaming signals, and history.
- `app/bridge/settings.py`: QWebChannel bridge for model selection and hardware acceleration.
- `app/bridge/model.py`: QWebChannel bridge for model download, local discovery, and status checks.
- `app/bridge/provider.py`: QWebChannel bridge for provider configurations (Local, Google, Anthropic, OpenAI).
- `app/bridge/window.py`: QWebChannel bridge for window management (minimize, maximize, close).
- `app/ui/index.html`: Web-based reactive frontend UI.
- `app/ui/marked.min.js`: Bundled Markdown parser for rendering chat messages.

### Core Domain Logic (`core/`)
- `core/__init__.py`: Core package marker.
- `core/config.py`: Centralized, validated environment configuration and constants.
- `core/conversation.py`: Multi-session in-memory conversation store with role separation.
- `core/db.py`: Safe SQLite database connection manager with corruption recovery and backup rotation.
- `core/errors.py`: Sanitized error formatting and diagnostic correlation tracking.
- `core/governance.py`: System governance rules and runtime execution guards.
- `core/hardware.py`: Hardware detection (CPU threads, GPU VRAM, CUDA/Metal capabilities).
- `core/knowledge_graph.py`: Learning Dependency Graph (LDG) backed by SQLite for prerequisite tracking.
- `core/logging_setup.py`: Rotating file logger and console logging configuration.
- `core/mode.py`: `AppMode` enum strictly separating Chemistry Tutor from General Assistant.
- `core/orchestrator.py`: Central routing orchestrator with transactional turn lifecycle and next-action resolution.
- `core/privacy.py`: PII redactor preventing personal identifiable information leakage.
- `core/profile.py`: Student profile management and learning preferences.
- `core/session.py`: Persistent session store for conversation and context restoration.
- `core/tutor_engine.py`: Chemistry tutoring engine coordinating concept progression and turn transactions.
- `core/validation.py`: Authoritative re-export shim for input validation.

### Agents & Runtimes (`core/agents/`, `core/runtimes/`)
- `core/agents/__init__.py`, `core/agents/policy.py`, `core/agents/registry.py`, `core/agents/runtime.py`: Agent execution policies, registry, and execution context.
- `core/runtimes/__init__.py`: Runtime package marker.
- `core/runtimes/chemistry.py`: Isolated Chemistry Tutor runtime with syllabus grounding.
- `core/runtimes/general.py`: Isolated General Assistant runtime with zero learning state mutation.

### Assessment Engine (`core/assessment/`)
- `core/assessment/__init__.py`: Package marker.
- `core/assessment/schema.py`: Question schema dataclasses (`MCQQuestion`, `NumericalQuestion`).
- `core/assessment/grader.py`: Rubric-based answer grader with numeric tolerances and unit checks.
- `core/assessment/generator.py`: NCERT question bank generator and topic selector.
- `core/assessment/adaptive.py`, `core/assessment/balancing.py`: Difficulty balancing and adaptive question sequencing.
- `core/assessment/manager.py`: Assessment session lifecycle manager with persistent attempt tracking and scoring.

### Curriculum Management (`core/curriculum/`)
- `core/curriculum/__init__.py`: Package marker.
- `core/curriculum/models.py`: Typed curriculum models (`CurriculumDomain`, `CurriculumManifest`).
- `core/curriculum/loader.py`: NCERT/CBSE curriculum manifest loader and query helpers.
- `core/curriculum/provider.py`: Curriculum provider with strict validation before graph seeding.
- `core/curriculum/resolver.py`: Concept ID resolver mapping user queries to canonical curriculum IDs.
- `core/curriculum/validator.py`: Strict DAG structural validator enforcing no cycles, no missing prerequisites, and valid difficulty levels.
- `core/curriculum/adapters.py`, `core/curriculum/dataset_registry.py`: Data adapters for external curriculum sets.

### Adaptive Learning Engine (`core/learning/`)
- `core/learning/__init__.py`: Package marker.
- `core/learning/events.py`: Append-only `LearningEvent` schema and factory.
- `core/learning/mastery.py`: Evidence-driven multi-factor mastery calculator ($0.0 \le \text{mastery} \le 1.0$).
- `core/learning/misconceptions.py`: Misconception tracker for chemistry misconception identification, recording, and remediation.
- `core/learning/policy.py`: Pedagogical policies for concept unlocking and progression.
- `core/learning/progress.py`: Learning progress analytics, mastery aggregation, and status labeling.
- `core/learning/scheduler.py`: Spaced review scheduler with retention delayed-recall verification.
- `core/learning/selector.py`: Adaptive concept selector using prerequisite readiness and review urgency.
- `core/learning/state.py`: Learning state definitions.

### Tutoring State Machine & Evaluation (`core/tutor/`)
- `core/tutor/__init__.py`: Package marker.
- `core/tutor/state.py`: `TutorStateManager` managing SQLite tables for events, mastery, and turn lifecycle.
- `core/tutor/state_machine.py`: Explicit 10-state tutoring lifecycle state machine.
- `core/tutor/evaluator.py`: `StudentAnswerEvaluator` providing rubric, numerical tolerance, and unit evaluation.
- `core/tutor/difficulty.py`: `DifficultyManager` managing adaptive difficulty bounded between L1 and L5.
- `core/tutor/lifecycle.py`: `TurnLifecycleManager` managing transactional turn persistence and startup recovery.
- `core/tutor/guard.py`: `OutOfDomainGuard` for politely redirecting non-chemistry queries.
- `core/tutor/memory.py`: Short-term and long-term tutoring memory tracking.
- `core/tutor/deadend.py`: `DeadEndResolver` and `NextAction` ensuring no state leaves the student without a valid next action.
- `core/tutor/decay.py`: Mastery decay modeling over time.
- `core/tutor/intents.py`: Student intent classification.
- `core/tutor/policies/__init__.py`, `explanation.py`, `numerical.py`, `reaction.py`: Specialized pedagogical policies for different chemistry topic formats.

### Security Hardening (`core/security/`)
- `core/security/__init__.py`: Package marker.
- `core/security/authorization.py`: Multi-student data isolation and authorization guard.
- `core/security/secrets.py`: Secure encrypted storage for provider API keys.
- `core/security/validation.py`: Zero-trust input validation (student IDs, session IDs, concept IDs, queries, file uploads).
- `core/security/prompt.py`: Prompt injection defense, system prompt delimiter armor, and student input sanitization.
- `core/security/upload.py`: Secure file upload manager with extension allowlists, magic byte verification, and bounded parsing.
- `core/security/rate_limiter.py`: Sliding window rate limiter and resource governor.
- `core/security/cache.py`: 6-dimensional student-isolated cache manager enforcing `Student A != Student B`.

### RAG & Retrieval Engine (`core/rag/`)
- `core/rag/__init__.py`: Package marker.
- `core/rag/schema.py`: Document chunk and search result schemas.
- `core/rag/ingester.py`: NCERT textbook ingestion and chunking engine.
- `core/rag/store.py`: Persistent vector/text chunk store.
- `core/rag/retriever.py`: Hybrid BM25/keyword retrieval with concept-aware filtering.
- `core/rag/citations.py`: Citation formatting and textbook source verification.

### Inference & Model Providers (`core/inference/`, `core/providers/`, `core/model_fetch/`)
- `core/inference/__init__.py`, `service.py`: Centralized model inference service.
- `core/providers/__init__.py`, `base.py`, `registry.py`: Provider abstract base and registry.
- `core/providers/local.py`: Local llama.cpp GGUF inference provider.
- `core/providers/google.py`: Google Gemini cloud provider with Local-Only privacy gating.
- `core/providers/anthropic.py`: Anthropic Claude cloud provider with Local-Only privacy gating.
- `core/providers/openai_compat.py`: OpenAI-compatible endpoint provider.
- `core/model_fetch/__init__.py`, `manifest_validator.py`, `ollama_pull.py`: Model manifest verification and SHA-256 integrity validation.

---

## 2. Development-Only Files

These files are essential for development, environment setup, and dependency management:
- `pyproject.toml`: Project metadata, dependencies, build configuration, and ruff/pytest settings.
- `requirements.txt`: Abstract Python dependencies.
- `requirements.lock`: Fully pinned dependency lockfile for reproducible environments.
- `.gitignore`: Git exclusion rules hardened per Section 31.
- `launch.bat`: One-click desktop launcher for Windows.
- `run_gayatri.bat`: Background launcher without console window.
- `setup.bat`: Automated environment setup and dependency installer.
- `install_llama.py`: VS C++ compiler detection and llama-cpp-python fallback build script (called from `setup.bat`).
- `gen_bridges.py`: Development code generator for PySide6 capability bridge scaffolds.

---

## 3. Test Files

All 36 test modules covering the complete verification suite (264 / 264 passed):
- `tests/test_phase2_startup.py`: Startup, dependencies, configuration, and environment audits.
- `tests/test_phase3_silent_failures.py`: Non-silent error propagation and error sanitization.
- `tests/test_phase4_student_isolation.py`: Cross-student data isolation and authorization.
- `tests/test_phase5_learning_events.py`: Learning event schema, persistence, and evidence updates.
- `tests/test_phase5_misconceptions.py`: Misconception catalog, detection, and tracking.
- `tests/test_phase6_evaluator.py`: Chemistry student answer evaluation and rubric matching.
- `tests/test_phase6_spaced_review.py`: Spaced repetition intervals and review queues.
- `tests/test_phase7_assessment_engine.py`: Assessment session generation and grading.
- `tests/test_phase7_concept_resolution.py`: Concept ID resolution and syllabus mapping.
- `tests/test_phase8_adaptive_engine.py`: Adaptive difficulty and state machine transitions.
- `tests/test_phase8_curriculum_validation.py`: Curriculum schema validation and cycle detection.
- `tests/test_phase9_misconceptions.py`: Misconception remediation and resolution.
- `tests/test_phase9_rag.py`: NCERT RAG retrieval, citations, and empty-query resilience.
- `tests/test_phase10_reliability.py`: Turn lifecycle state persistence and crash recovery.
- `tests/test_phase10_spaced_review.py`: Spaced review scheduling and delayed recall retention.
- `tests/test_phase11_assessment_engine.py`: Assessment attempt recording and scoring tables.
- `tests/test_phase11_mode_isolation.py`: Strict isolation between Chemistry and General Assistant.
- `tests/test_phase12_curriculum_validation.py`: DAG prerequisite validation and corruption fail-fast.
- `tests/test_phase12_progress.py`: ProgressService analytics and status labels.
- `tests/test_phase13_rag_audit.py`: RAG security, empty retrieval, and citation verification.
- `tests/test_phase13_silent_failures.py`: Zero silent failures and error sanitization.
- `tests/test_phase14_concurrency.py`: Concurrency limiting and thread safety.
- `tests/test_phase14_database.py`: Database connection safety and corruption recovery.
- `tests/test_phase15_database_hardening.py`: SQLite WAL mode, foreign keys, and transaction rollback.
- `tests/test_phase15_security.py`: Authorization guards and log sanitization.
- `tests/test_phase16_model_config.py`: Model manifest validation and SHA-256 checking.
- `tests/test_phase16_security_audit.py`: Security re-audit of secrets and data boundaries.
- `tests/test_phase17_final_matrix.py`: Master integration matrix.
- `tests/test_phase17_prompt_security.py`: Prompt injection defense and delimiter armor.
- `tests/test_phase18_input_validation.py`: Zero-trust input validation on all entry points.
- `tests/test_phase19_upload_security.py`: Secure upload handling, double extension blocking, and magic bytes.
- `tests/test_phase20_resource_limits.py`: Sliding window rate limiting and resource governors.
- `tests/test_phase21_cache_isolation.py`: 6-dimensional cache isolation (`Student A != Student B`).
- `tests/test_phase22_frontend_api.py`: Frontend/API reliability across all 10 interaction states.
- `tests/test_phase23_deadends.py`: Dead-end analysis across all 11 tutoring scenarios and 3 paths.
- `tests/test_phase24_hardening.py`: Property-style invariants, regression suite, and concurrency stress tests.

---

## 4. CI / Deployment Files

- `.github/workflows/ci.yml`: GitHub Actions continuous integration pipeline.
- `scripts/benchmark_performance.py`: End-to-end latency and throughput benchmarking.
- `scripts/package_release.py`: Standalone distribution packager.
- `scripts/verify_release.py`: Release verification and artifact checksum validator.

---

## 5. Training / RAG Resources

- `data/curriculum/chemistry/ncert_class11_12.json`: Canonical NCERT Class 11 and 12 Chemistry curriculum.
- `data/curriculum/chemistry/curriculum_manifest.json`: Structured domain manifest.
- `data/curriculum/math/grade9_cbse.json`, `python/beginner.json`, `science/grade9_ncert.json`: Multi-subject curriculum datasets.
- `training/prompts/chemistry_tutor_system_v1.txt`: System prompt for Chemistry Tutor.
- `training/prompts/general_assistant_system_v1.txt`: System prompt for General Assistant.
- `model_manifest.json`: Verified local model definitions with SHA-256 hashes.

---

## 6. Generated Artifacts (Cleaned)

The following untracked build, cache, and temporary directories were audited and removed:
- `.pytest_cache/`: Pytest cache directory.
- `.mypy_cache/`: Mypy type checker cache.
- `.ruff_cache/`: Ruff linter cache.
- `dist/`: Build outputs (`dist/gayatri-ai-v3.0.0/`).
- `scratch/`: Temporary audit and helper scripts.
- All `__pycache__/` subdirectories and `*.pyc` bytecode files across the workspace.

---

## 7. Proven Obsolete Source

**None.** Every source file in `app/`, `core/`, and `legacy/` was audited against static imports, dynamic references, and test suites. No functional source file was found to be obsolete.

---

## 8. Safe-to-Delete Files

The only files identified as safe to delete were untracked generated build artifacts and temporary caches:
- Untracked `dist/gayatri-ai-v3.0.0/` build output.
- Untracked `scratch/` directory containing temporary scripts.
- Python compilation artifacts (`__pycache__/`, `*.pyc`).

---

## 9. Human-Review Candidates

**None.** All deletion candidates were verified as purely generated artifacts. All source, configuration, and documentation files remain intact.

---

## 10. Files Intentionally Retained

1. `legacy/agents/default_agents.py`: Retained as a backward-compatibility shim for external or legacy callers.
2. `core/validation.py`: Retained as an authoritative re-export shim for `core/security/validation.py`.
3. `gen_bridges.py`: Retained as development tooling for bridge scaffolding.
4. `install_llama.py`: Retained as it is invoked by `setup.bat` when building local inference wheels.
5. `GayatriAI/`: Retained as local application runtime storage (`gayatri.db`, `settings.json`, `secrets.enc`).

---

## 11. Tests Run After Cleanup

The complete automated test suite was executed after all artifact removals:

```bash
pytest -q
```

**Result:**
- **264 passed** out of 264 tests across all 36 test modules in 6.48 seconds.
- **0 failed**, **0 errors**, **0 skipped**.
- **100% test pass rate maintained.**
