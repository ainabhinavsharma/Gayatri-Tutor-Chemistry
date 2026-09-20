# Gayatri Tutor Chemistry — Complete File Dependency Audit (Phase 1)

**Audit Date:** 2026-09-20  
**Repository:** `ainabhinavsharma/Gayatri-Tutor-Chemistry`  
**Total Tracked Files Analyzed:** 85  
**Deletions in this Phase:** 0 (Strict Safe Deletion Policy)  

---

## 1. Mandatory File Dependency Table (Section 33 Schema)

| Path | Classification | Runtime | Dynamic Ref | Test | Config Ref | Deployment | Recommendation | Confidence | Reason |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| `.github/workflows/ci.yml` | `CI_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Continuous integration workflow definition. |
| `.gitignore` | `DEVELOPMENT_TOOLING` | No | No | No | No | No | KEEP | HIGH | Development, build, or progress tracking tooling. |
| `app/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `app/bridge/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `app/bridge/chat.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `app/bridge/facade.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `app/bridge/model.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `app/bridge/provider.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `app/bridge/settings.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `app/bridge/window.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `app/install_hook.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `app/main.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `app/ui/index.html` | `RUNTIME_RESOURCE` | Yes | Yes | No | No | No | KEEP | HIGH | Required UI or data resource loaded at application runtime. |
| `app/ui/marked.min.js` | `RUNTIME_RESOURCE` | Yes | Yes | No | No | No | KEEP | HIGH | Required UI or data resource loaded at application runtime. |
| `app/windows/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `app/windows/main_window.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `CHANGELOG.md` | `DOCUMENTATION` | Yes | Yes | No | No | Yes | KEEP | HIGH | Architecture, design, or project documentation. |
| `CONTRIBUTING.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `core/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/agents/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/agents/policy.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/agents/registry.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 4 files. |
| `core/agents/runtime.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/assessment/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/assessment/adaptive.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/assessment/balancing.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/assessment/generator.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/assessment/grader.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/assessment/manager.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/assessment/schema.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 5 files. |
| `core/config.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 21 files. |
| `core/conversation.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/curriculum/adapters.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/curriculum/dataset_registry.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/curriculum/loader.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/curriculum/models.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | Yes | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/curriculum/provider.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/curriculum/resolver.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/curriculum/validator.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/db.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 8 files. |
| `core/errors.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | Yes | KEEP | HIGH | Essential application runtime module; imported by 9 files. |
| `core/governance.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/hardware.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/inference/service.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/knowledge_graph.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 6 files. |
| `core/learning/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/learning/events.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/learning/mastery.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/learning/misconceptions.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 6 files. |
| `core/learning/policy.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/learning/progress.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 4 files. |
| `core/learning/scheduler.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 5 files. |
| `core/learning/selector.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/learning/state.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/logging_setup.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/mode.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/model_fetch/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/model_fetch/manifest_validator.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/model_fetch/ollama_pull.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 4 files. |
| `core/orchestrator.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/privacy.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/profile.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/prompts/loader.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/providers/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/providers/anthropic.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/providers/base.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 6 files. |
| `core/providers/google.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/providers/local.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Essential application runtime module; imported by 7 files. |
| `core/providers/openai_compat.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/providers/registry.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/rag/citations.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/rag/ingester.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/rag/retriever.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/rag/schema.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 8 files. |
| `core/rag/store.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | Yes | Yes | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/research/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/research/defense.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/research/fallback.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/research/policy.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/research/service.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/runtimes/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/runtimes/chemistry.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/runtimes/general.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/safety.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/security/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/security/authorization.py` | `RUNTIME_REQUIRED` | Yes | No | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/security/secrets.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/security/signatures.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/session.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/settings.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 8 files. |
| `core/tutor/adapter.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/decay.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/difficulty.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/evaluator.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `core/tutor/guard.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/intents.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/lifecycle.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 2 files. |
| `core/tutor/memory.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/policies/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `core/tutor/policies/explanation.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/policies/numerical.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/policies/reaction.py` | `RUNTIME_REQUIRED` | Yes | No | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor/state.py` | `RUNTIME_REQUIRED` | Yes | Yes | Yes | No | No | KEEP | HIGH | Essential application runtime module; imported by 16 files. |
| `core/tutor/state_machine.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 1 files. |
| `core/tutor_engine.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 4 files. |
| `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `docs/INFERENCE_ARCHITECTURE.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `docs/LEGACY_AGENT_INVENTORY.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `docs/LLM_CALL_GRAPH.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `docs/PRIVACY_CONTRACT.md` | `DOCUMENTATION` | Yes | Yes | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `docs/REPOSITORY_ARCHITECTURE_CURRENT.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `docs/V4_PERFORMANCE_RECONCILIATION.md` | `DOCUMENTATION` | No | No | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `gen_bridges.py` | `DEVELOPMENT_TOOLING` | Yes | Yes | No | No | No | KEEP | HIGH | Development, build, or progress tracking tooling. |
| `install_llama.py` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `launch.bat` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `legacy/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `legacy/agents/__init__.py` | `RUNTIME_REQUIRED` | Yes | No | No | Yes | No | KEEP | HIGH | Essential application runtime module; imported by 0 files. |
| `legacy/agents/default_agents.py` | `RUNTIME_REQUIRED` | Yes | Yes | No | No | No | KEEP | HIGH | Essential application runtime module; imported by 3 files. |
| `LICENSE.md` | `DOCUMENTATION` | Yes | Yes | No | No | No | KEEP | HIGH | Architecture, design, or project documentation. |
| `model_manifest.json` | `RUNTIME_RESOURCE` | Yes | Yes | No | No | No | KEEP | HIGH | Required UI or data resource loaded at application runtime. |
| `PROGRESS_TRACKER.yaml` | `DEVELOPMENT_TOOLING` | No | No | No | No | No | KEEP | HIGH | Development, build, or progress tracking tooling. |
| `pyproject.toml` | `DEVELOPMENT_TOOLING` | Yes | Yes | No | No | Yes | KEEP | HIGH | Development, build, or progress tracking tooling. |
| `README.md` | `DOCUMENTATION` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Architecture, design, or project documentation. |
| `requirements.lock` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `requirements.txt` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `run_gayatri.bat` | `DEPLOYMENT_REQUIRED` | No | No | No | No | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `scripts/benchmark_performance.py` | `DEVELOPMENT_TOOLING` | Yes | Yes | No | No | No | KEEP | HIGH | Development, build, or progress tracking tooling. |
| `scripts/package_release.py` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `scripts/verify_release.py` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | No | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `setup.bat` | `DEPLOYMENT_REQUIRED` | Yes | Yes | No | Yes | Yes | KEEP | HIGH | Deployment, installation, or execution script. |
| `tests/test_phase10_reliability.py` | `TEST_REQUIRED` | No | Yes | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase11_mode_isolation.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase12_progress.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase13_silent_failures.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase14_database.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase15_security.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase16_model_config.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase17_final_matrix.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase5_misconceptions.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase6_spaced_review.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase7_assessment_engine.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase8_curriculum_validation.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `tests/test_phase9_rag.py` | `TEST_REQUIRED` | No | No | Yes | No | No | KEEP | HIGH | Automated test suite verifying core components and regression invariants. |
| `VERSION` | `RUNTIME_RESOURCE` | Yes | Yes | No | No | Yes | KEEP | HIGH | Required UI or data resource loaded at application runtime. |

---

## 2. Detailed Per-File Audit Records (Section 4 Schema)

### `.github/workflows/ci.yml`
- **Classification:** `CI_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** Yes
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Continuous integration workflow definition.

### `.gitignore`
- **Classification:** `DEVELOPMENT_TOOLING`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Development, build, or progress tracking tooling.

### `app/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `app/bridge/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/windows/main_window.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `app/bridge/chat.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/windows/main_window.py`
- **Dynamic References (1):** `gen_bridges.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `app/bridge/facade.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (4):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`, `docs/V4_PERFORMANCE_RECONCILIATION.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `app/bridge/model.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/windows/main_window.py`
- **Dynamic References (1):** `gen_bridges.py`
- **Configuration References (3):** `model_manifest.json`, `core/config.py`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `app/bridge/provider.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/windows/main_window.py`
- **Dynamic References (1):** `gen_bridges.py`
- **Configuration References (2):** `core/config.py`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `app/bridge/settings.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/windows/main_window.py`
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `gen_bridges.py`
- **Configuration References (2):** `core/config.py`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `app/bridge/window.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/windows/main_window.py`
- **Dynamic References (1):** `gen_bridges.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** Yes
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `app/install_hook.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `app/main.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (1):** `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `app/ui/index.html`
- **Classification:** `RUNTIME_RESOURCE`
- **Direct Importers (0):** None
- **Dynamic References (4):** `app/windows/main_window.py`, `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `docs/V4_PERFORMANCE_RECONCILIATION.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Required UI or data resource loaded at application runtime.

### `app/ui/marked.min.js`
- **Classification:** `RUNTIME_RESOURCE`
- **Direct Importers (0):** None
- **Dynamic References (1):** `app/ui/index.html`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Required UI or data resource loaded at application runtime.

### `app/windows/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `app/windows/main_window.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/main.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `CHANGELOG.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `scripts/package_release.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `CONTRIBUTING.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `core/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/agents/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/agents/policy.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/agents/registry.py`, `core/agents/runtime.py`
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/agents/registry.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (4):** `app/bridge/facade.py`, `core/agents/__init__.py`, `core/agents/runtime.py`, `core/orchestrator.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 4 files.

### `core/agents/runtime.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `app/bridge/facade.py`, `core/agents/__init__.py`, `core/orchestrator.py`
- **Dynamic References (3):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (1):** `requirements.txt`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/assessment/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/assessment/adaptive.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/assessment/balancing.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/assessment/grader.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/assessment/generator.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/assessment/grader.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/assessment/manager.py`, `tests/test_phase7_assessment_engine.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/assessment/manager.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `tests/test_phase17_final_matrix.py`, `tests/test_phase7_assessment_engine.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/assessment/schema.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (5):** `core/assessment/adaptive.py`, `core/assessment/generator.py`, `core/assessment/grader.py`, `core/assessment/manager.py`, `tests/test_phase7_assessment_engine.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 5 files.

### `core/config.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (21):** `app/bridge/facade.py`, `app/install_hook.py`, `app/main.py`, `app/windows/main_window.py`, `core/agents/runtime.py`, `core/governance.py`, `core/hardware.py`, `core/knowledge_graph.py`, `core/logging_setup.py`, `core/model_fetch/ollama_pull.py`, `core/orchestrator.py`, `core/profile.py`, `core/providers/base.py`, `core/providers/local.py`, `core/providers/registry.py`, `core/rag/store.py`, `core/security/secrets.py`, `core/session.py`, `core/settings.py`, `core/tutor/state.py`, `core/tutor_engine.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (2):** `requirements.lock`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 21 files.

### `core/conversation.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/orchestrator.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/curriculum/adapters.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/curriculum/dataset_registry.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/curriculum/loader.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/knowledge_graph.py`, `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/curriculum/models.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/curriculum/loader.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `core/config.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/curriculum/provider.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/curriculum/loader.py`
- **Dynamic References (1):** `gen_bridges.py`
- **Configuration References (2):** `core/config.py`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/curriculum/resolver.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/runtimes/chemistry.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/curriculum/validator.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `tests/test_phase17_final_matrix.py`, `tests/test_phase8_curriculum_validation.py`
- **Dynamic References (3):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/db.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (8):** `core/governance.py`, `core/knowledge_graph.py`, `core/profile.py`, `core/rag/store.py`, `core/session.py`, `core/tutor/state.py`, `tests/test_phase14_database.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 8 files.

### `core/errors.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (9):** `app/bridge/facade.py`, `app/install_hook.py`, `core/agents/runtime.py`, `core/orchestrator.py`, `core/providers/anthropic.py`, `core/providers/google.py`, `core/providers/openai_compat.py`, `tests/test_phase13_silent_failures.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (1):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 9 files.

### `core/governance.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/hardware.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/model_fetch/ollama_pull.py`, `core/providers/local.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/inference/service.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/runtimes/chemistry.py`, `core/runtimes/general.py`
- **Dynamic References (1):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/knowledge_graph.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (6):** `app/bridge/facade.py`, `core/curriculum/adapters.py`, `core/curriculum/provider.py`, `core/governance.py`, `core/orchestrator.py`, `core/tutor_engine.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 6 files.

### `core/learning/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/learning/events.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/learning/__init__.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/learning/mastery.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/assessment/manager.py`, `core/learning/__init__.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (1):** `core/config.py`
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/learning/misconceptions.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (6):** `core/assessment/manager.py`, `core/learning/__init__.py`, `core/learning/progress.py`, `tests/test_phase12_progress.py`, `tests/test_phase17_final_matrix.py`, `tests/test_phase5_misconceptions.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 6 files.

### `core/learning/policy.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/learning/__init__.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/learning/progress.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (4):** `core/learning/__init__.py`, `core/tutor/state.py`, `tests/test_phase12_progress.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 4 files.

### `core/learning/scheduler.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (5):** `core/learning/__init__.py`, `core/learning/progress.py`, `core/tutor/state.py`, `tests/test_phase17_final_matrix.py`, `tests/test_phase6_spaced_review.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 5 files.

### `core/learning/selector.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/learning/__init__.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/learning/state.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/logging_setup.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `app/bridge/facade.py`, `app/main.py`
- **Dynamic References (1):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/mode.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/orchestrator.py`, `tests/test_phase11_mode_isolation.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/model_fetch/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/model_fetch/manifest_validator.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `tests/test_phase16_model_config.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/model_fetch/ollama_pull.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (4):** `app/bridge/facade.py`, `app/install_hook.py`, `core/model_fetch/__init__.py`, `core/providers/local.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 4 files.

### `core/orchestrator.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `app/bridge/facade.py`, `core/knowledge_graph.py`
- **Dynamic References (5):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`, `docs/V4_PERFORMANCE_RECONCILIATION.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/privacy.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/orchestrator.py`
- **Dynamic References (0):** None
- **Configuration References (2):** `core/config.py`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/profile.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/tutor/adapter.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/prompts/loader.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/runtimes/chemistry.py`, `core/runtimes/general.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/providers/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/providers/anthropic.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/providers/__init__.py`, `core/providers/registry.py`
- **Dynamic References (2):** `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/providers/base.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (6):** `core/providers/__init__.py`, `core/providers/anthropic.py`, `core/providers/google.py`, `core/providers/local.py`, `core/providers/openai_compat.py`, `core/providers/registry.py`
- **Dynamic References (3):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 6 files.

### `core/providers/google.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/providers/__init__.py`, `core/providers/registry.py`
- **Dynamic References (2):** `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/providers/local.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (7):** `app/bridge/facade.py`, `app/install_hook.py`, `core/orchestrator.py`, `core/providers/__init__.py`, `core/providers/registry.py`, `legacy/agents/default_agents.py`, `scripts/benchmark_performance.py`
- **Dynamic References (3):** `docs/INFERENCE_ARCHITECTURE.md`, `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (2):** `core/config.py`, `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 7 files.

### `core/providers/openai_compat.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `core/providers/__init__.py`, `core/providers/registry.py`
- **Dynamic References (2):** `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/providers/registry.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `app/bridge/facade.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/rag/citations.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `tests/test_phase9_rag.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/rag/ingester.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/rag/retriever.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/runtimes/chemistry.py`, `tests/test_phase17_final_matrix.py`, `tests/test_phase9_rag.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/rag/schema.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (8):** `core/rag/citations.py`, `core/rag/ingester.py`, `core/rag/retriever.py`, `core/rag/store.py`, `core/research/fallback.py`, `core/runtimes/chemistry.py`, `tests/test_phase17_final_matrix.py`, `tests/test_phase9_rag.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 8 files.

### `core/rag/store.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/rag/retriever.py`, `tests/test_phase17_final_matrix.py`, `tests/test_phase9_rag.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/research/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/research/defense.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/research/service.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/research/fallback.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/research/policy.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/research/fallback.py`, `core/research/service.py`, `core/runtimes/chemistry.py`
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/research/service.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (1):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/runtimes/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/runtimes/chemistry.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/orchestrator.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `model_manifest.json`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/runtimes/general.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/orchestrator.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/safety.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (1):** `core/config.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/security/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/security/authorization.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/security/__init__.py`, `tests/test_phase15_security.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/security/secrets.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `app/bridge/facade.py`, `core/providers/registry.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/security/signatures.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/model_fetch/ollama_pull.py`, `scripts/package_release.py`, `scripts/verify_release.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/session.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `app/bridge/facade.py`, `core/orchestrator.py`, `core/tutor_engine.py`
- **Dynamic References (3):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/settings.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (8):** `app/bridge/facade.py`, `app/bridge/settings.py`, `core/agents/runtime.py`, `core/orchestrator.py`, `core/providers/base.py`, `core/providers/registry.py`, `core/research/policy.py`, `core/runtimes/general.py`
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `gen_bridges.py`
- **Configuration References (1):** `core/config.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 8 files.

### `core/tutor/adapter.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (1):** `model_manifest.json`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/decay.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/tutor_engine.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/difficulty.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/evaluator.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/runtimes/chemistry.py`, `core/tutor/difficulty.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `core/tutor/guard.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/intents.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/lifecycle.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (2):** `tests/test_phase10_reliability.py`, `tests/test_phase17_final_matrix.py`
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 2 files.

### `core/tutor/memory.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/policies/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `core/tutor/policies/explanation.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/policies/numerical.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/policies/reaction.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor/state.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (16):** `core/assessment/manager.py`, `core/learning/events.py`, `core/learning/mastery.py`, `core/learning/misconceptions.py`, `core/learning/policy.py`, `core/learning/progress.py`, `core/learning/scheduler.py`, `core/learning/selector.py`, `core/learning/state.py`, `core/tutor/lifecycle.py`, `tests/test_phase10_reliability.py`, `tests/test_phase12_progress.py`, `tests/test_phase17_final_matrix.py`, `tests/test_phase5_misconceptions.py`, `tests/test_phase6_spaced_review.py`, `tests/test_phase7_assessment_engine.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 16 files.

### `core/tutor/state_machine.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (1):** `core/runtimes/chemistry.py`
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 1 files.

### `core/tutor_engine.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (4):** `app/bridge/facade.py`, `core/orchestrator.py`, `core/session.py`, `core/tutor/decay.py`
- **Dynamic References (2):** `CHANGELOG.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 4 files.

### `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `docs/INFERENCE_ARCHITECTURE.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `docs/LEGACY_AGENT_INVENTORY.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `docs/LLM_CALL_GRAPH.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `docs/PRIVACY_CONTRACT.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `docs/V4_PERFORMANCE_RECONCILIATION.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `gen_bridges.py`
- **Classification:** `DEVELOPMENT_TOOLING`
- **Direct Importers (0):** None
- **Dynamic References (1):** `PROGRESS_TRACKER.yaml`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Development, build, or progress tracking tooling.

### `install_llama.py`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `PROGRESS_TRACKER.yaml`, `setup.bat`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `launch.bat`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `scripts/package_release.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `legacy/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `legacy/agents/__init__.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (1):** `core/settings.py`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 0 files.

### `legacy/agents/default_agents.py`
- **Classification:** `RUNTIME_REQUIRED`
- **Direct Importers (3):** `core/inference/service.py`, `core/runtimes/chemistry.py`, `core/runtimes/general.py`
- **Dynamic References (4):** `docs/LEGACY_AGENT_INVENTORY.md`, `docs/LLM_CALL_GRAPH.md`, `docs/REPOSITORY_ARCHITECTURE_CURRENT.md`, `docs/V4_PERFORMANCE_RECONCILIATION.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Essential application runtime module; imported by 3 files.

### `LICENSE.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (1):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `model_manifest.json`
- **Classification:** `RUNTIME_RESOURCE`
- **Direct Importers (0):** None
- **Dynamic References (4):** `core/model_fetch/manifest_validator.py`, `README.md`, `tests/test_phase16_model_config.py`, `tests/test_phase17_final_matrix.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Required UI or data resource loaded at application runtime.

### `PROGRESS_TRACKER.yaml`
- **Classification:** `DEVELOPMENT_TOOLING`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Development, build, or progress tracking tooling.

### `pyproject.toml`
- **Classification:** `DEVELOPMENT_TOOLING`
- **Direct Importers (0):** None
- **Dynamic References (3):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `PROGRESS_TRACKER.yaml`, `scripts/package_release.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Development, build, or progress tracking tooling.

### `README.md`
- **Classification:** `DOCUMENTATION`
- **Direct Importers (0):** None
- **Dynamic References (3):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `pyproject.toml`, `scripts/package_release.py`
- **Configuration References (1):** `pyproject.toml`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Architecture, design, or project documentation.

### `requirements.lock`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (3):** `CHANGELOG.md`, `requirements.txt`, `scripts/package_release.py`
- **Configuration References (1):** `requirements.txt`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** Yes
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `requirements.txt`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (5):** `.github/workflows/ci.yml`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `README.md`, `scripts/package_release.py`, `setup.bat`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** Yes
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `run_gayatri.bat`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `scripts/benchmark_performance.py`
- **Classification:** `DEVELOPMENT_TOOLING`
- **Direct Importers (0):** None
- **Dynamic References (1):** `docs/LLM_CALL_GRAPH.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Development, build, or progress tracking tooling.

### `scripts/package_release.py`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `scripts/verify_release.py`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (2):** `CHANGELOG.md`, `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `setup.bat`
- **Classification:** `DEPLOYMENT_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (5):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `install_llama.py`, `launch.bat`, `run_gayatri.bat`, `scripts/package_release.py`
- **Configuration References (2):** `pyproject.toml`, `requirements.lock`
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** Yes
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Deployment, installation, or execution script.

### `tests/test_phase10_reliability.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (1):** `README.md`
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase11_mode_isolation.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase12_progress.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase13_silent_failures.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase14_database.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase15_security.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase16_model_config.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase17_final_matrix.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase5_misconceptions.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase6_spaced_review.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase7_assessment_engine.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase8_curriculum_validation.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `tests/test_phase9_rag.py`
- **Classification:** `TEST_REQUIRED`
- **Direct Importers (0):** None
- **Dynamic References (0):** None
- **Configuration References (0):** None
- **Runtime Required:** No
- **Test Required:** Yes
- **Deployment Required:** No
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Automated test suite verifying core components and regression invariants.

### `VERSION`
- **Classification:** `RUNTIME_RESOURCE`
- **Direct Importers (0):** None
- **Dynamic References (2):** `docs/GAYATRI_TUTOR_V3_ENGINEERING_TRACKER.md`, `scripts/package_release.py`
- **Configuration References (0):** None
- **Runtime Required:** Yes
- **Test Required:** No
- **Deployment Required:** Yes
- **CI Required:** No
- **Generated:** No
- **Duplicate:** No
- **Recommendation:** **KEEP**
- **Confidence:** HIGH
- **Reason:** Required UI or data resource loaded at application runtime.
