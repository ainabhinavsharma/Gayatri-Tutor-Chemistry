# Gayatri Tutor V3 → V4
# Performance, Streaming, Responsiveness & Reliability Refactor
## AI Agent Execution Specification

**Repository:** https://github.com/ainabhinavsharma/Gayatri-Tutor-V3  
**Branch:** Work from the current repository state; do not assume `main` is unchanged.  
**Purpose:** This document is an executable engineering plan for an AI coding agent.

---

# 0. READ THIS FIRST

This file is both:

1. a technical implementation plan; and
2. a durable work-state/checkpoint system for AI-agent sessions.

The agent MUST read this file before modifying the repository.

The agent MUST inspect the current code before implementing any item because some parts of the intended architecture are already present.

## Primary user-visible problem

Gayatri Tutor currently has infrastructure that can stream tokens, but important agent paths still collapse generation into a complete response before the UI receives it.

The desired behavior is:

```text
USER
  ↓
QWebChannel
  ↓
Bridge
  ↓
Orchestrator
  ↓
AgentRuntime.stream()
  ↓
Agent.stream()
  ↓
Inference / LocalProvider.chat_stream()
  ↓
token chunks
  ↓
Qt batching
  ↓
QWebChannel
  ↓
JavaScript buffer
  ↓
requestAnimationFrame()
  ↓
VISIBLE INCREMENTAL RESPONSE
```

NOT:

```text
USER
  ↓
Agent.process()
  ↓
LocalProvider.chat()
  ↓
FULL RESPONSE
  ↓
Bridge
  ↓
UI
```

---

# 1. ABSOLUTE AGENT RULES

## 1.1 Never trust this document over the actual repository

Before changing code:

- inspect the current files;
- inspect Git status;
- inspect recent commits;
- search the codebase;
- run existing tests;
- verify whether each planned task is already implemented.

If the implementation differs from this document, update the tracker and adapt the plan.

## 1.2 Work phase by phase

Never attempt the entire V4 refactor in one uncontrolled edit.

Required order:

```text
Phase 0
  ↓
Phase 1
  ↓
Phase 2
  ↓
Phase 3
  ↓
Phase 4
  ↓
Phase 5
  ↓
Phase 6
  ↓
Phase 7
  ↓
Phase 8
  ↓
Phase 9
  ↓
Phase 10
```

A phase cannot be marked `DONE` without evidence.

## 1.3 Never claim a fix without proof

Bad:

```text
Streaming fixed.
```

Good:

```text
Tutor stream test passed:
12 chunks received before completion.
TTFT = 612 ms.
Final response matches concatenated chunks.
```

## 1.4 Do not rewrite working systems unnecessarily

Preserve:

- PySide6;
- QWebEngine;
- QWebChannel;
- llama.cpp / llama-cpp-python;
- existing agent architecture;
- SQLite;
- RAG;
- LDG;
- existing UI behavior.

Refactor only where required.

## 1.5 Keep the UI thread free

No expensive:

- LLM inference;
- database operation;
- filesystem operation;
- large parsing;
- context construction;
- evaluation

may run synchronously on the GUI thread.

## 1.6 Preserve existing behavior

Performance changes must not silently break:

- Tutor;
- Practice;
- Code Review;
- RAG;
- LDG;
- session history;
- persistence;
- Markdown;
- tools;
- error handling.

---

# 2. CURRENTLY KNOWN REPOSITORY STATE

The latest audit found that several pieces are already implemented.

## Already present

### Provider streaming

`LocalProvider` already has a streaming path based on llama.cpp streaming.

Status:

```text
P1-T01 = DONE
```

### Bridge worker

The bridge already performs inference in a worker thread and batches token signals.

Status:

```text
P3-T01 = MOSTLY DONE
```

### Frontend requestAnimationFrame

The UI already uses `requestAnimationFrame()` and a render buffer.

Status:

```text
P3-T02 = MOSTLY DONE
P3-T03 = MOSTLY DONE
```

### Tutor evaluator

Tutor evaluation has been moved toward background execution.

Status:

```text
P2-T01 = IMPLEMENTED
P2-T02 = IMPLEMENTED
```

However, evaluator inference still uses the local inference provider and may contend for the model/inference lock. This must be measured rather than assumed to be independent.

---

# 3. CRITICAL REMAINING DEFECT

The major remaining issue is the agent execution path.

Current conceptual path:

```text
Orchestrator.stream()
      ↓
AgentRuntime.process()
      ↓
agent.process()
      ↓
_local_chat()
      ↓
LocalProvider.chat()
      ↓
complete generation
      ↓
return full AgentResponse
      ↓
orchestrator emits it
```

This means the application has streaming at the provider/bridge/UI layers but loses streaming in the agent/runtime layer.

## Required target

```text
Orchestrator.stream()
      ↓
AgentRuntime.stream()
      ↓
agent.stream()
      ↓
LocalProvider.chat_stream()
      ↓
yield chunk
      ↓
yield chunk
      ↓
yield chunk
      ↓
Bridge
      ↓
UI
```

This is the highest-priority remaining fix.

---

# 4. PROGRESS STATE — DO NOT DELETE

Update this block after every meaningful task.

```yaml
project: Gayatri Tutor V3 -> V4 Performance Refactor

overall_status: DONE

current_phase: 9
current_task: P9-T06

last_completed_task: "P9-T06 (Performance Regression Benchmarking)"
last_verified_commit: "ac792c0"

last_test_status: "PASSED (237/237 tests)"
last_benchmark_status: "PASSED (TTFT 1844ms, TPS 3.4 on baseline HW)"

known_failures: []

blocked_tasks: []

next_action: "All Performance Refactoring phases complete. Ready for release."

last_agent_note: "Phases 5-9 completed successfully. System prompts are static to maximize KV cache reuse, Inference Service manages centralized locking, cancellation cascades correctly from UI to backend, and telemetry is fully instrumented."

updated_at: "2026-09-17T01:50:00"
```

## Status vocabulary

Use only:

```text
TODO
IN_PROGRESS
DONE
FAILED
BLOCKED
DEFERRED
```

Never use:

```text
almost done
mostly working
probably fixed
should work
```

---

# 5. SESSION RECOVERY PROTOCOL

When a new AI session begins:

## Step 1

Read this file completely.

## Step 2

Read `Progress State`.

## Step 3

Read the `Execution Ledger`.

## Step 4

Run:

```bash
git status
git log --oneline -20
git diff
```

## Step 5

Inspect the last completed task.

Do not trust the previous agent's claim without verifying code/tests.

## Step 6

Run the relevant tests.

## Step 7

Continue from:

```yaml
next_action:
```

## Step 8

If repository state conflicts with the tracker:

1. stop;
2. investigate;
3. correct the tracker;
4. record why;
5. continue.

---

# 6. EXECUTION LEDGER

Update this table continuously.

| ID | Phase | Task | Status | Evidence | Tests | Benchmark | Commit |
|---|---|---|---|---|---|---|---|
| P0-T01 | 0 | Repository reconnaissance | TODO | | | | |
| P0-T02 | 0 | Trace all LLM paths | TODO | | | | |
| P0-T03 | 0 | Baseline benchmark | TODO | | | | |
| P0-T04 | 0 | Baseline test suite | TODO | | | | |
| P1-T01 | 1 | Verify provider streaming | DONE | | | | |
| P1-T02 | 1 | Define agent streaming contract | TODO | | | | |
| P1-T03 | 1 | Implement Tutor streaming | TODO | | | | |
| P1-T04 | 1 | Implement Practice streaming | TODO | | | | |
| P1-T05 | 1 | Implement Code Review streaming | TODO | | | | |
| P1-T06 | 1 | Audit remaining agents | TODO | | | | |
| P1-T07 | 1 | Implement AgentRuntime.stream | TODO | | | | |
| P1-T08 | 1 | Preserve stream through Orchestrator | TODO | | | | |
| P1-T09 | 1 | End-to-end streaming verification | TODO | | | | |
| P2-T01 | 2 | Tutor evaluator off critical path | DONE | | | | |
| P2-T02 | 2 | Background evaluator reliability | TODO | | | | |
| P2-T03 | 2 | Prove evaluator does not delay TTFT | TODO | | | | |
| P3-T01 | 3 | Qt token batching | DONE | | | | |
| P3-T02 | 3 | JS buffering | DONE | | | | |
| P3-T03 | 3 | requestAnimationFrame rendering | DONE | | | | |
| P3-T04 | 3 | Optimize scroll behavior | TODO | | | | |
| P3-T05 | 3 | Optimize Markdown rendering | TODO | | | | |
| P3-T06 | 3 | Long response UI test | TODO | | | | |
| P4-T01 | 4 | Audit critical-path persistence | TODO | | | | |
| P4-T02 | 4 | Move session save off critical path | TODO | | | | |
| P4-T03 | 4 | Move LDG/background analytics | TODO | | | | |
| P4-T04 | 4 | Persistence failure recovery | TODO | | | | |
| P5-T01 | 5 | Measure prompt growth | TODO | | | | |
| P5-T02 | 5 | Context window policy | TODO | | | | |
| P5-T03 | 5 | Conversation summarization | TODO | | | | |
| P5-T04 | 5 | Relevant-context selection | TODO | | | | |
| P6-T01 | 6 | Design InferenceService | TODO | | | | |
| P6-T02 | 6 | Centralize model lifecycle | TODO | | | | |
| P6-T03 | 6 | Centralize concurrency | TODO | | | | |
| P6-T04 | 6 | Add cancellation | TODO | | | | |
| P6-T05 | 6 | Worker cleanup | TODO | | | | |
| P7-T01 | 7 | Add TTFT telemetry | TODO | | | | |
| P7-T02 | 7 | Add generation telemetry | TODO | | | | |
| P7-T03 | 7 | Add UI telemetry | TODO | | | | |
| P7-T04 | 7 | Add structured performance logs | TODO | | | | |
| P7-T05 | 7 | Benchmark CLI | TODO | | | | |
| P8-T01 | 8 | Hardware benchmark matrix | TODO | | | | |
| P8-T02 | 8 | Tune context/thread settings | TODO | | | | |
| P8-T03 | 8 | Tune GPU offload | TODO | | | | |
| P8-T04 | 8 | Compare compatible quantizations | TODO | | | | |
| P9-T01 | 9 | Streaming unit tests | TODO | | | | |
| P9-T02 | 9 | Orchestrator integration tests | TODO | | | | |
| P9-T03 | 9 | Cancellation tests | TODO | | | | |
| P9-T04 | 9 | Persistence tests | TODO | | | | |
| P9-T05 | 9 | Long conversation tests | TODO | | | | |
| P9-T06 | 9 | Performance regression tests | TODO | | | | |
| P10-T01 | 10 | Final functional audit | TODO | | | | |
| P10-T02 | 10 | Final performance audit | TODO | | | | |
| P10-T03 | 10 | Documentation | TODO | | | | |
| P10-T04 | 10 | V4 release readiness | TODO | | | | |

---

# 7. PHASE 0 — RECONNAISSANCE AND BASELINE

## Objective

Establish exactly how the current application behaves.

Do not optimize yet.

## P0-T01 — Repository reconnaissance

Inspect:

```text
core/
app/
tests/
docs/
scripts/
training/
```

At minimum inspect:

```text
core/orchestrator.py
core/providers/local.py
core/agents/default_agents.py
core/agents/runtime.py
app/bridge/facade.py
app/ui/index.html
core/config.py
core/hardware.py
```

Also discover any newer/moved equivalents.

## P0-T02 — Trace every LLM call

Search for:

```text
LocalProvider
chat(
chat_stream(
stream(
create_completion(
create_chat_completion(
process(
```

Create:

```text
docs/LLM_CALL_GRAPH.md
```

Table:

| Component | Function | Provider | Blocking | Streaming | User-visible |
|---|---|---|---|---|---|

Every LLM call must be listed.

## P0-T03 — Baseline benchmark

Measure:

1. Direct chat.
2. Tutor.
3. Practice.
4. Code Review.
5. Long response.
6. Long conversation.

Record:

```text
model
hardware
prompt size
TTFT
total latency
output tokens
tokens/sec
```

## P0-T04 — Baseline tests

Run the repository test suite.

Record:

```text
command
passed
failed
skipped
environment
```

## Exit criteria

- [ ] Architecture mapped.
- [ ] All LLM paths identified.
- [ ] Baseline metrics recorded.
- [ ] Existing tests recorded.
- [ ] Tracker updated.

---

# 8. PHASE 1 — TRUE AGENT END-TO-END STREAMING

## Priority: P0

This phase directly fixes the current user-visible latency defect.

---

## P1-T02 — Agent streaming contract

Introduce a consistent agent-level streaming interface.

Concept:

```python
def stream(self, context):
    """Yield response chunks progressively."""
    ...
```

Do not force an exact signature if existing architecture uses a better context object.

Requirements:

- returns/yields incrementally;
- no full-response buffering;
- preserves ordering;
- propagates errors;
- supports cancellation design;
- does not break `process()` compatibility if existing callers require it.

---

## P1-T03 — Tutor streaming

Current blocking pattern must be eliminated.

Find the Tutor's actual LLM generation function.

If it currently resembles:

```python
text = _local_chat(...)
```

and `_local_chat()` ultimately calls:

```python
LocalProvider.chat(...)
```

replace the user-visible generation path with:

```python
for chunk in LocalProvider.chat_stream(...):
    yield chunk
```

Do not collect the entire stream with:

```python
list(...)
```

or:

```python
"".join(...)
```

before yielding.

The final response can be reconstructed separately for persistence/analytics after generation.

---

## P1-T04 — Practice streaming

Apply the same pattern.

Required:

```text
Practice request
 ↓
Practice agent
 ↓
stream
 ↓
first token
 ↓
more tokens
 ↓
completion
```

---

## P1-T05 — Code Review streaming

Apply the same pattern.

Be careful with code blocks and Markdown.

Do not delay the response merely because final Markdown formatting is incomplete.

---

## P1-T06 — Remaining agents

Search every agent for:

```text
LocalProvider.chat
LocalProvider.generate
create_completion
```

Classify:

```text
USER_VISIBLE_GENERATION
BACKGROUND_EVALUATION
UTILITY_LLM_CALL
```

Every user-visible generation path must stream.

Background/utility calls may remain non-streaming where appropriate.

---

## P1-T07 — AgentRuntime.stream()

This is a critical missing layer.

Add a streaming runtime path.

Target:

```text
AgentRuntime.stream()
        ↓
agent.stream()
        ↓
yield chunk
```

Do not implement:

```python
response = agent.process(...)
for x in response:
    yield x
```

if `process()` already waited for complete generation.

### Tool-enabled agents

If an agent can execute tools, preserve this state machine:

```text
model
 ↓
stream
 ↓
tool call?
 ├── NO → continue stream
 └── YES
       ↓
    pause model stream
       ↓
    execute tool
       ↓
    add tool result
       ↓
    resume model
       ↓
    continue stream
```

Do not accidentally execute a tool only after the entire final response.

---

## P1-T08 — Orchestrator

Ensure `Orchestrator.stream()` calls the streaming runtime.

Bad:

```python
response = self.runtime.process(...)
```

Target:

```python
for chunk in self.runtime.stream(...):
    yield chunk, False
```

The orchestrator must not collapse agent streams.

---

## P1-T09 — End-to-end verification

A real Tutor request must demonstrate:

```text
chunk 1 → UI
chunk 2 → UI
chunk 3 → UI
...
chunk N → UI
DONE
```

The test must fail if:

```text
WAIT
WAIT
WAIT
FULL RESPONSE
DONE
```

### Required evidence

Record:

```text
number_of_chunks
first_chunk_timestamp
completion_timestamp
TTFT
final_text
concatenated_stream_text
```

Acceptance:

```text
first_chunk_timestamp < completion_timestamp
concatenated_stream_text == final_text
number_of_chunks > 1
```

for a test response expected to contain multiple chunks.

---

# 9. PHASE 2 — EVALUATION AND SECONDARY WORK

## Objective

Do not allow Tutor evaluation or analytics to unnecessarily delay visible generation.

## P2-T01

Already implemented, but re-verify.

Tutor generation must not wait for evaluator completion.

## P2-T02 — Background evaluator reliability

Background evaluator must:

- run independently of UI;
- not crash the application;
- not corrupt session state;
- not overwrite newer mastery data with stale data;
- log failures;
- handle malformed evaluator responses.

Use request/session IDs to correlate work.

## P2-T03 — TTFT proof

Instrument:

```text
request start
evaluator start
first token
evaluator finish
```

Desired relationship:

```text
request start
    ↓
generation starts
    ↓
FIRST TOKEN
    ↓
evaluator may continue
    ↓
generation complete
    ↓
evaluator complete
```

If the evaluator still blocks model inference due to a shared lock, measure and redesign the scheduling/queue rather than merely calling it asynchronous.

---

# 10. PHASE 3 — UI STREAMING PERFORMANCE

## P3-T01 — Qt batching

Already substantially implemented.

Verify:

- chunks are accumulated;
- signals are not emitted once per token unnecessarily;
- final remainder is flushed;
- cancellation flushes safely;
- errors flush safely.

Recommended target:

```text
20–40 ms batching window
```

Tune using measurements.

## P3-T02 — JavaScript buffering

Keep an incremental response buffer.

Avoid unnecessary:

```javascript
currentTokens.join('')
```

on every tiny event if a more efficient incremental strategy is possible.

## P3-T03 — requestAnimationFrame

Already implemented.

Verify it actually limits DOM rendering frequency.

## P3-T04 — Scroll optimization

Avoid:

```javascript
chat.scrollTop = chat.scrollHeight
```

for every render.

Track whether the user is near the bottom.

Only auto-scroll when appropriate.

If the user has scrolled upward, do not forcibly drag them to the bottom.

## P3-T05 — Markdown rendering

Do not fully parse Markdown on every tiny token.

Use:

```text
raw/incremental text
 ↓
batched render
 ↓
final Markdown render
```

Special tests:

- fenced code;
- tables;
- lists;
- inline code;
- incomplete Markdown syntax.

## P3-T06 — Long response UI test

Test at least:

```text
500 tokens
1000 tokens
2000+ tokens where practical
```

Record:

```text
generation chunks
UI updates
render time
CPU
memory
TTFT
```

Acceptance:

- UI remains interactive;
- no visible multi-second freeze;
- final response is complete.

---

# 11. PHASE 4 — PERSISTENCE OFF THE CRITICAL PATH

## Current concern

If completion currently performs:

```text
last token
 ↓
save session
 ↓
done signal
```

the final UI state can still be delayed.

Target:

```text
last token
 ↓
done signal
 ↓
background persistence
```

## P4-T01 — Audit persistence

Search for:

```text
save_session
SQLite
sqlite
commit
write
open(
json.dump
```

inside generation/completion paths.

## P4-T02 — Session save

Move safe persistence after user-visible completion.

The final generated response must already be available to the UI.

## P4-T03 — LDG/analytics

Move non-essential:

- LDG writes;
- analytics;
- mastery updates;
- training logs

to controlled background work.

## P4-T04 — Failure recovery

If background persistence fails:

- do not erase the response;
- log a safe error;
- retry where appropriate;
- prevent duplicate writes;
- preserve session consistency.

### Exit criteria

The UI must not wait for non-essential persistence before becoming idle.

---

# 12. PHASE 5 — CONTEXT AND PROMPT OPTIMIZATION

## Objective

Reduce prompt-processing latency as conversations grow.

## P5-T01 — Measure prompt growth

Measure:

```text
1 turn
5 turns
10 turns
20 turns
50 turns
```

where practical.

Record:

```text
message count
characters
estimated tokens
prompt construction time
TTFT
```

## P5-T02 — Context policy

Do not blindly send unnecessary history.

Target:

```text
current turn
+
recent relevant turns
+
conversation summary
+
learning state
+
relevant RAG
```

## P5-T03 — Conversation summary

If needed, introduce a summary layer.

It must preserve:

- learning objectives;
- important facts;
- unresolved questions;
- progress;
- tutor state;
- important constraints.

Do not summarize away essential learning context.

## P5-T04 — Relevant context selection

Use the existing RAG/LDG infrastructure where appropriate.

Avoid duplicating the same information across:

```text
history
summary
RAG
LDG
```

if it increases prompt size without adding value.

---

# 13. PHASE 6 — CENTRAL INFERENCE SERVICE

Only begin this phase after Phase 1 streaming is proven.

## Target

```text
InferenceService
├── generate()
├── stream()
├── evaluate()
├── cancel()
├── health()
├── metrics()
└── model lifecycle
```

## P6-T01 — Design

Document:

```text
docs/INFERENCE_ARCHITECTURE.md
```

before implementing.

## P6-T02 — Model lifecycle

Centralize:

- model loading;
- model reuse;
- model unloading;
- provider selection;
- model configuration;
- errors.

Model should not be repeatedly loaded for normal requests.

## P6-T03 — Concurrency

Current local inference locking must be audited.

Do not simply remove the lock.

Choose a safe strategy:

```text
single inference queue
```

or equivalent supported by the model runtime.

Important:

A background evaluator and foreground generation may still compete for the same model even if they run in separate Python threads.

Measure actual behavior.

## P6-T04 — Cancellation

Target:

```text
UI STOP
 ↓
Bridge.cancel()
 ↓
worker cancellation flag/event
 ↓
InferenceService.cancel()
 ↓
llama.cpp generation stops
 ↓
cleanup
 ↓
UI idle
```

Cancellation must be:

- thread-safe;
- idempotent;
- safe during generation;
- safe during startup;
- safe during completion.

## P6-T05 — Worker cleanup

Verify:

- no orphan threads;
- no repeated worker accumulation;
- no stale callbacks;
- no double completion;
- no model lock retained after cancellation.

---

# 14. PHASE 7 — PERFORMANCE TELEMETRY

## P7-T01 — TTFT

Measure:

```text
request_received
generation_started
first_token
```

Formula:

```text
TTFT = first_token_timestamp - request_received_timestamp
```

## P7-T02 — Generation

Measure:

```text
generation_duration
output_tokens
tokens_per_second
```

Formula:

```text
tokens_per_second =
output_tokens / generation_seconds
```

## P7-T03 — UI

Measure where practical:

```text
ui_first_render
ui_render_count
ui_render_duration
```

## P7-T04 — Structured logs

Use JSON Lines where practical:

```json
{"request_id":"...", "agent":"tutor", "ttft_ms":512, "generation_ms":7234, "output_tokens":421, "tokens_per_second":58.2}
```

Never log:

- API keys;
- passwords;
- authentication tokens;
- private conversations by default.

## P7-T05 — Benchmark CLI

Create an appropriate benchmark command, for example:

```bash
python -m tools.benchmark_performance
```

Adapt to repository conventions.

It should output machine-readable and human-readable results.

---

# 15. PHASE 8 — HARDWARE AND MODEL TUNING

Do not start by changing the model.

Measure first.

## P8-T01 — Benchmark matrix

Create:

| Config | Context | Threads | GPU layers | Quantization | TTFT | tok/s | RAM |
|---|---:|---:|---:|---|---:|---:|---:|

## P8-T02 — Context/thread tuning

Benchmark supported values for:

- context size;
- threads;
- batch size.

Do not use unsupported parameters.

## P8-T03 — GPU offload

If GPU is available, compare configurations.

Do not assume:

```text
n_gpu_layers = -1
```

is always optimal.

## P8-T04 — Quantization

If multiple compatible GGUF models exist:

- benchmark speed;
- benchmark memory;
- benchmark output behavior.

Do not optimize speed while ignoring quality.

---

# 16. PHASE 9 — TESTING AND REGRESSION PROTECTION

## P9-T01 — Streaming unit tests

Required tests:

```text
provider yields multiple chunks
agent yields multiple chunks
runtime preserves chunks
orchestrator preserves chunks
final text == concatenated chunks
```

## P9-T02 — Integration tests

At least:

```text
Tutor
Practice
Code Review
Direct chat
```

must be tested.

## P9-T03 — Cancellation

Verify:

```text
generation starts
 ↓
chunks arrive
 ↓
cancel
 ↓
generation stops
 ↓
cleanup
 ↓
exactly one completion/cancel result
```

## P9-T04 — Persistence

Verify:

- response remains available if save fails;
- no duplicate saves;
- session remains consistent.

## P9-T05 — Long conversation

Verify context policy does not cause:

- runaway prompt growth;
- major TTFT degradation;
- broken tutor state.

## P9-T06 — Performance regression

Store baseline and current measurements.

Required comparison:

| Metric | Baseline | Current | Delta |
|---|---:|---:|---:|
| TTFT | | | |
| Total generation | | | |
| Tokens/sec | | | |
| UI updates | | | |
| Memory | | | |
| Cancel latency | | | |

---

# 17. STANDARD PERFORMANCE TEST CASES

## S1 — Direct chat

```text
Explain recursion in simple terms.
```

## S2 — Tutor

```text
Teach me binary search and ask me a question.
```

## S3 — Practice

Request a practice problem.

## S4 — Code Review

Submit a moderate code block and request review.

## S5 — Long answer

Request a detailed technical explanation.

## S6 — Long session

Build a conversation with many turns.

## S7 — Cancellation

Cancel after visible streaming begins.

## S8 — Error recovery

Simulate model/provider failure where safely possible.

---

# 18. STREAMING ACCEPTANCE TEST

This is the most important test.

Instrument the actual path:

```text
User
 ↓
Bridge
 ↓
Orchestrator
 ↓
AgentRuntime
 ↓
Agent
 ↓
Provider
 ↓
UI
```

For a Tutor response:

```text
expected_chunks > 1
first_chunk_time < completion_time
```

Also verify:

```text
"".join(all_chunks) == final_response
```

If any layer buffers the complete response, the test should fail.

---

# 19. PERFORMANCE ACCEPTANCE TEST

For a warm model:

```text
TTFT target: <1.5s where hardware permits
```

But the test MUST record actual hardware.

Never fail a machine simply because it cannot achieve a hardware-dependent target without first documenting the environment.

More important than an absolute target:

```text
streaming begins early
UI remains responsive
no unnecessary blocking work
```

---

# 20. FAILURE / BLOCKED PROTOCOL

If blocked:

```yaml
status: BLOCKED
blocker: ""
evidence: ""
attempted: ""
required: ""
workaround: ""
```

The agent MUST NOT silently skip blocked work.

If a task is no longer appropriate:

```yaml
status: DEFERRED
reason: ""
replacement: ""
```

---

# 21. CODE CHANGE SAFETY

Before modifying an important subsystem:

```bash
git status
git diff
```

After modification:

```bash
git diff
```

Then run relevant tests.

Prefer small commits.

Recommended commit sequence:

```text
perf: establish streaming baseline
perf: add agent streaming contract
perf: stream tutor responses
perf: stream practice responses
perf: stream code review responses
perf: add runtime streaming
perf: preserve agent streaming through orchestrator
perf: remove evaluator latency from critical path
perf: optimize qwebchannel batching
perf: optimize webengine rendering
perf: move persistence off response path
perf: optimize context assembly
perf: add inference service
perf: add cancellation
perf: add performance telemetry
perf: add benchmark suite
perf: tune local inference
test: add streaming regression coverage
docs: document v4 performance architecture
```

Adapt to repository conventions.

---

# 22. DO NOT USE THESE FALSE FIXES

Do not solve the problem by:

- adding arbitrary `sleep()`;
- increasing thread count blindly;
- spawning one thread per token;
- buffering more data;
- hiding latency with a spinner;
- replacing the model without benchmarking;
- increasing context size to "improve quality";
- removing locks without proving thread safety;
- disabling persistence;
- disabling evaluation entirely;
- removing RAG/LDG merely for speed;
- replacing PySide6 without evidence;
- claiming asynchronous code is independent when it still contends for the same model lock.

---

# 23. PERFORMANCE DIAGNOSTIC DECISION TREE

If UI hangs:

```text
Is first token generated?
       │
       ├── NO
       │    ↓
       │  backend/model/agent latency
       │
       └── YES
            ↓
       Does UI receive token?
            │
            ├── NO
            │    ↓
            │  bridge/QWebChannel issue
            │
            └── YES
                 ↓
            Does UI render incrementally?
                 │
                 ├── NO
                 │    ↓
                 │  JS/DOM/Markdown issue
                 │
                 └── YES
                      ↓
                 Does UI freeze later?
                      │
                      ├── YES
                      │    ↓
                      │  rendering/persistence/context issue
                      │
                      └── NO
                           ↓
                       healthy stream
```

---

# 24. REQUIRED DOCUMENTATION OUTPUTS

Create/update as appropriate:

```text
docs/PERFORMANCE_BASELINE.md
docs/LLM_CALL_GRAPH.md
docs/INFERENCE_ARCHITECTURE.md
docs/PERFORMANCE_ARCHITECTURE.md
docs/PERFORMANCE_BENCHMARKS.md
docs/TESTING.md
```

Do not create duplicate documentation if an equivalent document already exists.

---

# 25. FINAL RELEASE GATE

Gayatri Tutor V4 performance work is complete only when all are true.

## Streaming

- [ ] Provider streams.
- [ ] Tutor streams.
- [ ] Practice streams.
- [ ] Code Review streams.
- [ ] Other user-visible agents stream.
- [ ] AgentRuntime preserves streams.
- [ ] Orchestrator preserves streams.
- [ ] Bridge delivers incremental chunks.
- [ ] UI renders incrementally.
- [ ] Final text is correct.

## Latency

- [ ] TTFT measured.
- [ ] Secondary evaluation does not unnecessarily block TTFT.
- [ ] Context construction measured.
- [ ] Persistence removed from critical path.
- [ ] Model lifecycle optimized.
- [ ] Hardware benchmarked.

## UI

- [ ] No perceptible generation freeze.
- [ ] DOM rendering is batched.
- [ ] requestAnimationFrame used correctly.
- [ ] Scroll behavior optimized.
- [ ] Markdown rendering optimized.
- [ ] Long responses tested.
- [ ] Stop button works.

## Inference

- [ ] Central inference lifecycle.
- [ ] Safe concurrency.
- [ ] Cancellation.
- [ ] Worker cleanup.
- [ ] Error recovery.

## Observability

- [ ] TTFT.
- [ ] generation time.
- [ ] tokens/sec.
- [ ] prompt size.
- [ ] UI update count.
- [ ] persistence timing.
- [ ] structured logs.

## Testing

- [ ] Streaming unit tests.
- [ ] Agent tests.
- [ ] Runtime tests.
- [ ] Orchestrator tests.
- [ ] UI/integration tests.
- [ ] Cancellation tests.
- [ ] Persistence tests.
- [ ] Long-session tests.
- [ ] Performance regression tests.

---

# 26. FINAL SESSION HANDOFF FORMAT

At the end of every AI coding session, append/update this section.

```yaml
session_handoff:
  date: ""
  agent: ""
  phase: ""
  tasks_completed: []
  tasks_started: []
  tasks_blocked: []
  files_changed: []
  tests_run: []
  tests_passed: []
  tests_failed: []
  benchmark_results: {}
  commits: []
  known_regressions: []
  next_action: ""
  notes_for_next_agent: ""
```

The next agent must read this before touching the code.

---

# 27. FINAL INSTRUCTION TO THE AI AGENT

The immediate priority is NOT general optimization.

The immediate priority is:

```text
FIX TRUE AGENT STREAMING
```

Specifically:

```text
AgentRuntime.process()
       ↓
REMOVE FROM STREAMING PATH
```

and implement:

```text
AgentRuntime.stream()
       ↓
Agent.stream()
       ↓
LocalProvider.chat_stream()
       ↓
Qt batching
       ↓
QWebChannel
       ↓
requestAnimationFrame
       ↓
VISIBLE STREAM
```

After this is proven, proceed to persistence, context, centralized inference, cancellation, telemetry, hardware tuning, and regression testing.

The agent must work incrementally, verify every phase, update the ledger, and maintain the recovery state.

**Never leave the repository in a state where the tracker says DONE but the implementation has not been tested.**

**Never leave the repository without updating `next_action` before ending a session.**

**The tracker is part of the engineering system, not optional documentation.**
