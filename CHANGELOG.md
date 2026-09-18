# Changelog

All notable changes to the Gayatri Tutor V3 project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-09-16

### Added
- **Cryptographic Security & Signing (Phase 5):**
  - Implemented asymmetric Ed25519 signature engine (`core/security/signatures.py`).
  - Signed model manifest verification in `core/model_fetch/ollama_pull.py` preventing untrusted weights execution.
  - Automated release packaging (`scripts/package_release.py`) and cryptographic verification CLI (`scripts/verify_release.py`).
- **Productization & Governance (Phase 4):**
  - Multi-user profile management (`core/profile.py`) with profile-scoped session tracking (`core/session.py`).
  - Standardized bilingual CBSE Mathematics and NCERT Science curriculum adapters (`core/curriculum/adapters.py`).
  - Age-band safety policies and academic integrity guardrails (`core/safety.py`).
  - Parent/teacher administrative PIN protection, daily screen-time limits, and progress reporting in JSON and CSV (`core/governance.py`).
- **Engineering Maturity & Reliability (Phase 2 & 3):**
  - Automated schema migration and corruption recovery framework (`core/db.py`).
  - Learning Dependency Graph recovery mode (`core/knowledge_graph.py`, `core/tutor_engine.py`).
  - Provider lifecycle state tracking and capability-based fallback routing (`core/providers/registry.py`).
  - 3-gram Jaccard similarity training/evaluation leakage prevention (`training/validators/dataset_validator.py`).
  - Python 3.12 locked dependencies (`requirements.lock`) and GitHub Actions CI (`.github/workflows/ci.yml`).
- **Core Security & Privacy Hardening (Phase 0 & 1):**
  - Windows DPAPI secure secret storage (`core/security/secrets.py`).
  - QWebChannel bridge privilege restrictions and Content Security Policy (`app/ui/index.html`).
  - Multi-turn LLM intent evaluator for student mastery verification (`core/orchestrator.py`).
  - Formal local-only privacy contract and network audit transmission log (`docs/PRIVACY_CONTRACT.md`, `core/providers/base.py`).

### Changed
- Refactored brittle source-text assertions into behavioral test fixtures.
- Decoupled `LLMProvider` base class from singleton local provider assumptions.
- Upgraded SQLite connections to enforce WAL mode, synchronous=NORMAL, and foreign key constraints across concurrent worker threads.

### Verified
- 100% test pass rate across 228 automated behavioral and regression tests.
- Section 31 "Production-Ready" Acceptance Gate fully satisfied.
