# Gayatri Tutor V4 — Performance & Architecture Refactor Plan

## Executive Summary
While Gayatri Tutor V3 successfully implements the agentic architecture and local model loading, there are several bottlenecks related to **Time-To-First-Token (TTFT)**, **Inter-Process Communication (IPC)** overhead, and **synchronous blocking**. 

This document outlines a phase-by-phase development plan to refactor the performance architecture, ensuring instant response times, smooth UI rendering, and efficient hardware utilization.

---

## Phase 1: Unblocking the Tutor Agent & True Streaming
**Goal:** Eliminate the 5-10 second delay before the Tutor agent starts typing.
**Current Bottleneck:** The `_evaluate_tutor_response()` method in `core/orchestrator.py` runs a full, synchronous, hidden LLM inference pass to grade the student's answer *before* the visible streaming response is allowed to start.

### Tasks
- [x] **Decouple Assessment:** Move student evaluation (`_evaluate_tutor_response`) out of the critical path. It should run asynchronously as a background task *while* or *after* the main response streams to the user.
- [x] **Token Buffering (IPC Optimization):** Currently, every single token (1-3 characters) emits a `token` signal over PySide6's `QWebChannel`. This creates massive IPC overhead. Implement a buffer in `facade.py` that yields chunks of tokens every ~50ms instead of instantly.
- [x] **Background Task Queue:** Implement a lightweight `asyncio` or `ThreadPoolExecutor` queue for the orchestrator to fire-and-forget non-UI tasks (like telemetry and grading).

---

## Phase 2: LLM Engine & Context Caching (TTFT Optimization)
**Goal:** Reduce Time-To-First-Token (TTFT) by reusing the system prompt and conversation history computations.
**Current Bottleneck:** `llama-cpp-python` re-evaluates the entire prompt (System Prompt + History + New Message) on every single turn.

### Tasks
- [x] **Enable Prompt Caching:** Modify `core/providers/local.py` to enable `llama-cpp` state caching (e.g., passing `prompt_cache` or managing `llama_state`).
- [x] **Prefix Retention:** Lock the system prompt and agent instructions in memory so the model only calculates attention for the *new* user messages, cutting TTFT by up to 60%.
- [x] **Dynamic VRAM Offloading:** Currently, `LOCAL_MODEL_GPU_LAYERS` is static. Implement a check during model load that polls `core/hardware.py` for actual available VRAM and dynamically adjusts the `n_gpu_layers` to prevent swapping to system RAM.

---

## Phase 3: Database & State Management
**Goal:** Prevent SQLite database locking or UI stuttering during high-speed interactions.
**Current Bottleneck:** Session updates and Knowledge Graph (LDG) state changes are written synchronously.

### Tasks
- [x] **Async SQLite Writes:** Move `core/session.py` DB writes (like `_save_session_by_id`) to a background writer thread. Use an in-memory queue to batch conversation saves.
- [x] **WAL Mode Verification:** Ensure `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` are explicitly enforced on the `sqlite-vec` connections to allow concurrent reads/writes without blocking the LLM inference.
- [x] **Lazy LDG Loading:** The Learning Dependency Graph parses JSON heavily. Cache the parsed state in memory and only flush to disk periodically.

---

## Phase 4: Frontend UI Rendering Engine
**Goal:** Ensure 60fps scrolling and rendering during generation.
**Current Bottleneck:** Appending text to the DOM and re-parsing Markdown on every single token causes layout thrashing (Reflow/Repaint loops).

### Tasks
- [x] **Markdown Debouncing:** In `app/ui/index.html`, do not run the Markdown parser on every token. Parse raw text during the stream, and only run the heavy Markdown/Math rendering when the stream pauses or completes.
- [x] **RequestAnimationFrame (rAF):** Wrap the `updateLastMessage()` DOM updates in `window.requestAnimationFrame()` to sync UI updates with the monitor's refresh rate, eliminating jank.
- [x] **Virtual Scrolling:** If the chat history gets very long (50+ messages), the DOM becomes heavy. Implement a simple virtual scroller or hide off-screen messages to maintain performance.

---

## Proposed Execution Order
1. **Immediate:** Execute **Phase 1** (Token Buffering & Tutor Async Grading). This provides the most noticeable impact to the user.
2. **Next:** Execute **Phase 2** (LLM Caching) to optimize hardware usage.
3. **Long-Term:** Execute **Phases 3 & 4** as polish items before a stable V4 release.
