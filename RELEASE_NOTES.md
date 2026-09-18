# Gayatri AI Tutor V3 - Release Notes

**Version:** 3.0.0  
**Release Date:** September 16, 2026  
**License:** Apache 2.0  
**Platform:** Windows 10/11 (x64)

---

## 1. System & Architecture Overview

Gayatri Tutor V3 is an on-device, privacy-first AI educational tutor engineered to deliver personalized Socratic instruction across standardized national curricula without compromising student data.

### Release Identification & Specifications
| Component | Specification |
|---|---|
| **Application Version** | `3.0.0` |
| **Local Model Engine** | GGUF via `llama-cpp-python` (0.3.x) & Ollama Registry API |
| **Recommended Model** | Gemma 2 2B / 9B Instruct (`Q4_K_M` quantization) |
| **Curriculum Version** | `CBSE-Math-G9-v1`, `NCERT-Science-G9-v1` |
| **Dataset Standard** | `Synthetic-Curriculum-v3` (3-gram Jaccard leakage-free) |
| **Python Runtime** | Python 3.12.x (64-bit) |
| **GUI Framework** | PySide6 / Qt 6.11.x (Chromium QWebEngine with Strict CSP) |
| **Database Engine** | SQLite 3 with Write-Ahead Logging (WAL) and auto-migrations |
| **Cryptographic Signatures** | Ed25519 (RFC 8032) & SHA-256 integrity manifests |

---

## 2. Key Capabilities

### Privacy-Preserving Socratic Instruction
- **Local-Only Privacy Tier:** In `LOCAL_ONLY` execution mode, network transmission is physically barred; inference occurs exclusively on the local machine.
- **Evidence-Calibrated Mastery:** Student knowledge assessment requires demonstrated multi-turn problem solving rather than simple keyword matches.
- **Academic Integrity Guardrails:** Cheating attempts (e.g., asking the tutor to solve an exam question directly) are intercepted and redirected to Socratic guided practice.

### Multi-User Architecture & Governance
- **Profile Isolation:** Distinct learner profiles maintain separate mastery graphs, session histories, and settings.
- **Parent & Teacher Oversight:** Protected with administrative PIN locks, screen-time limits, and automated progress exports (CSV/JSON).

### Cryptographic Release & Model Verification
- Every release bundle contains a signed `RELEASE_MANIFEST.json` with cryptographic SHA-256 digests.
- Model downloads support cryptographic signature validation against official trust anchors before model loading.

---

## 3. Hardware Requirements

- **Minimum:**
  - CPU: Intel Core i5 (8th Gen+) or AMD Ryzen 5 with AVX2 support
  - RAM: 8 GB System Memory
  - Storage: 10 GB free disk space (SSD recommended)
  - OS: Windows 10 (Build 19041+) or Windows 11 64-bit
- **Recommended:**
  - CPU: 8 cores or higher
  - RAM: 16 GB System Memory
  - GPU: NVIDIA GPU with >= 6 GB VRAM (CUDA 12.x) for accelerated inference

---

## 4. Known Operational Limitations

1. **First-Run Model Download:** The initial local model download requires an active internet connection to pull the approved model weights, after which the application operates completely offline.
2. **High Token Contexts:** On systems without dedicated GPU VRAM, context sizes exceeding 4,096 tokens may experience slower generation speeds (3-5 tokens/sec).
