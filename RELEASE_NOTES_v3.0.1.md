# Gayatri Chemistry Tutor v3.0.1 — Production SLM Edition

**Edition:** Production SLM Edition (Ultra-Lite)  
**Target Syllabus:** Senior Secondary (CBSE Class 11 & 12 / NCERT Aligned)  
**Execution Profile:** 100% Offline • Local Neural Inference (Qwen2.5-0.5B Socratic SLM) • Embedded SQLite  
**Data Privacy:** Zero Cloud Connectivity • Zero Telemetry Egress • Strictly Air-Gapped Local Operation  

---

## 🌟 The Vision

Education is most effective when it is **interactive, encouraging, and Socratic**. 

Generic AI chatbots fail in education because they **spoon-feed final numerical answers**, depriving learners of the cognitive struggle necessary to master chemistry. Furthermore, existing cloud AI systems demand costly subscription fees, constant internet connectivity, and compromise student privacy.

**Gayatri Chemistry Tutor** solves this paradigm through localized neural intelligence:
- **Pure Socratic Pedagogy:** Never reveals final solutions prematurely; guides students through analogies, targeted questions, and misconception remediation.
- **Zero Digital Divide:** Runs 100% offline on standard consumer hardware (including school laptops with 8 GB RAM) without requiring internet or expensive GPUs.
- **Absolute Data Sovereignty:** Student chats, mastery records, and cognitive progress remain strictly on the local machine with zero telemetry or cloud egress.

---

## ⚡ Technical Highlights & Production Benchmarks

### 🧠 1. Socratic Pre-Training & Alignment
- **Domain Specialization:** Fine-tuned on **2,500 curated Socratic dialogue trajectories** specifically calibrated to the NCERT/CBSE senior secondary chemistry syllabus.
- **5 Pedagogical Pillars Hardcoded in Model Weights:**
  1. **`EXPLAIN` Mode:** 4-tier scaffolding (Everyday Intuition $\to$ Formal Definition $\to$ Mathematical Law $\to$ Comprehension Check).
  2. **`QUESTION` Mode:** Calibrated numerical and conceptual problem posing.
  3. **`EVALUATE` Mode:** Real-time misconception diagnosis governed by the **Anti-Answer-Leakage Invariant** (diagnoses physical reasoning errors without giving away numerical answers).
  4. **`HINT` Mode:** Graduated 5-tier directional nudges.
  5. **`REMEDIATE` Mode:** Dynamic prerequisite backtracking along the curriculum dependency graph.

### 🔍 2. Sub-10ms Atomic Knowledge Retrieval (RAG)
- **Zero-VRAM Architecture:** Replaces heavy vector embedding models with lightweight, deterministic keyword and BM25 concept resolution.
- **Atomic Micro-Cards:** Structured curriculum cards (<75 tokens per card) providing factual NCERT grounding in **< 8 ms** retrieval time.
- **Coverage:** Chemical Thermodynamics (First Law, Hess's Law, Enthalpy, Entropy, Gibbs Free Energy), Chemical Bonding (VSEPR, Hybridisation, Molecular Geometry), and Periodic Trends.

### 💻 3. Real-World Hardware Benchmarks

| Performance Metric | Standard Student Laptop (8 GB RAM) | Desktop / Workstation (16 GB+ RAM) |
|---|---|---|
| **Target Processor** | Intel Core i3 / i5 (8th Gen+) or AMD Ryzen 3000 | Intel Core i7 / i9 or AMD Ryzen 5000+ |
| **Model Size on Disk** | **379.4 MB** (`Q4_K_M` 4-bit Medium quantization) | **379.4 MB** |
| **Active Inference RAM** | **~450 MB** | **~450 MB** |
| **Total App Footprint (GUI + WebEngine + Model)** | **~650 – 850 MB** total active memory | **~750 – 900 MB** total active memory |
| **Generation Latency (TTFT)** | **< 200 ms** to first streaming token | **< 120 ms** to first streaming token |
| **Streaming Speed** | **18 – 28 tokens / second** (smooth streaming) | **28 – 42 tokens / second** |
| **Application Cold Startup** | **< 2.4 seconds** (frameless animated splash) | **< 1.8 seconds** |
| **External Network Bandwidth** | **0.0 KB/s (Strictly Air-Gapped)** | **0.0 KB/s (Strictly Air-Gapped)** |

---

## 🛠️ What's New & Fixed in v3.0.1

1. **Native DLL Crash Eliminated (`llama-cpp-python` v0.3+):**
   - Implemented pre-import runtime hook resolving `ggml-base.dll`, `ggml-cpu.dll`, `ggml.dll`, and `llama.dll` properly inside the frozen bundle across all Windows versions.
2. **90% Package Size Reduction:**
   - Stripped unused debug WebEngine assets and software renderers.
   - **Setup Installer shrank from 1.95 GB → 143 MB!**
   - **Portable ZIP shrank from 2.04 GB → 210 MB!**
3. **Automated 1-Click Model Placement:**
   - Created `setup_model.bat` to automatically detect and stage `Gayatri-Tutor-SLM-Q4_K_M.gguf` from the user's `Downloads` folder in under 3 seconds.
4. **Clean Installation Experience:**
   - Eliminated command prompt terminal pop-up after setup wizard completes.
5. **Modern Animated Splash Screen:**
   - Frameless dark-themed card with lotus branding, smooth animated progress, and minimum 2.4-second guarantee to ensure full engine readiness before showing the workspace.

---

## 📦 Download Packages

| Asset | Format | File Size | Description |
|---|---|---|---|
| **`Gayatri_Chemistry_Tutor_v3.0.1_Setup.exe`** | Windows Installer | **143.4 MB** | **Standard Installer:** Setup wizard that installs to local user directory (no admin rights needed), creates Desktop & Start Menu shortcuts with lotus branding, and includes an uninstaller. |
| **`Gayatri_Chemistry_Tutor_Portable_v3.0.1.zip`** | Portable ZIP | **210.3 MB** | **Zero-Install Portable:** Extract to any folder or USB pen drive and run `Gayatri_Chemistry_Tutor.exe`. 100% self-contained with no registry footprint. |
| **`Gayatri-Tutor-SLM-Q4_K_M.gguf`** | Model Weights | **379.4 MB** | Fine-tuned 0.5B Socratic Small Language Model weights. |
| **`SHA256SUMS.txt`** | Checksums | 1 KB | Cryptographic SHA-256 integrity verification hashes. |
| **`GETTING_STARTED_GUIDE.md`** | User Guide | 5 KB | Quick start guide and 6 interactive hands-on learning exercises. |

---

## 🚀 2-Minute Quick Start

1. Download **`Gayatri_Chemistry_Tutor_v3.0.1_Setup.exe`** (or the Portable ZIP).
2. Download **`Gayatri-Tutor-SLM-Q4_K_M.gguf`** (379 MB) to your `Downloads` folder.
3. Install or extract the package.
4. Double-click **`setup_model.bat`** in the application folder (it will auto-detect the model from your `Downloads` folder and install it in seconds).
5. Launch **`Gayatri Chemistry Tutor`** from your desktop.

---

## 🔒 Cryptographic Verification

| File Name | SHA-256 Integrity Hash |
|---|---|
| `Gayatri_Chemistry_Tutor_v3.0.1_Setup.exe` | `89eb2e60dbeff15e30d9ad84f34747c8451febe218b333181d156daeb6d99e1c` |
| `Gayatri_Chemistry_Tutor_Portable_v3.0.1.zip` | `c252efafef3bf47519f1740764a91f49d7713d858f4d497546c4070dd785e19f` |
| `Gayatri-Tutor-SLM-Q4_K_M.gguf` | `eb4d05df2bf3eb7405d24742ade2622fc3f98b4be2b75d92dc2c00339d2b952b` |
| `GETTING_STARTED_GUIDE.md` | `b2fc48634b0f65bae74caa027d9615d82ff11f732023753bafd406ef2da13628` |

---

*Developed by Gayatri Education — Shaping the Future of NCERT Socratic AI Tutoring.*
