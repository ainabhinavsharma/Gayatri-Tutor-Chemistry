# V4 Performance Plan Reconciliation

This document reconciles the contradictory state found in the old `Gayatri_Tutor_V4_Performance_Refactor_EXECUTION_PLAN.md` where the progress section declared the refactor "DONE", while the execution ledger left multiple tasks as "TODO".

## Verified Claims (DONE)

The following items claimed as DONE in the ledger have been verified as correctly implemented in the codebase:
- **P1-T01 (Verify provider streaming):** Verified. `LocalProvider.chat_stream()` exists and implements chunking.
- **P2-T01 (Tutor evaluator off critical path):** Partially implemented/Mostly Done. `_evaluate_tutor_response` is called asynchronously via `threading.Thread` in `orchestrator.py` during normal streaming execution, though a synchronous path remains for fallback.
- **P3-T01 (Qt token batching):** Verified. `app/bridge/facade.py` batches tokens into 50ms chunks before emitting via QWebChannel.
- **P3-T02 & P3-T03 (JS buffering & rAF):** Verified. `app/ui/index.html` uses `window.requestAnimationFrame` and a 50ms `setTimeout` debounce for markdown rendering.

## Stale Claims (TODO / Not Done)

The "overall_status: DONE" claim in the V4 plan's progress state is false. The refactor was abandoned mid-way. The following critical items remain untouched or incomplete:
- **P1-T02 to P1-T09 (True Agent Streaming):** Not implemented. `default_agents.py` and `prompt_agents.py` still construct full responses via `LocalProvider` in synchronous contexts or pseudo-streaming wrappers that don't fully pipe up to the Orchestrator as requested.
- **Phases 4 through 10:** All marked as TODO in the ledger and no evidence of implementation exists in the codebase (no `InferenceService`, no persistent TTFT telemetry, no advanced LRU prompt caching).

## Conclusion
The old V4 performance refactor is **INCOMPLETE**. The architectural improvements (token batching, rAF) are valid and retained, but the global streaming and LLM offloading tasks will be absorbed or replaced by the new Chemistry/General Architecture plan where appropriate. We will not carry over the stale `DONE` status to the new project tracker.
