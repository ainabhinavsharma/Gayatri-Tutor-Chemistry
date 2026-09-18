# Gayatri Tutor V3 → Chemistry Tutor + General Assistance
## Phase-by-Phase AI Agent Development & Recovery Plan

**Repository:** https://github.com/ainabhinavsharma/Gayatri-Tutor-V3  
**Target branch:** Work from the actual local checkout; do not assume `main` is unchanged.  
**Plan created:** 2026-09-18  
**Execution model:** Local AI coding agent working incrementally in the repository  
**Primary target:** Convert the current multi-agent Gayatri Tutor V3 into a focused, local-first application with exactly two user-facing modes:

1. **Chemistry Tutor**
2. **General Assistant**

The existing legacy/specialized agents may remain in the repository temporarily for historical/reusable code, but they must be **disabled and unreachable at runtime**. The application must not expose, route to, or accidentally invoke old agents.

---

# 0. READ THIS FIRST — NON-NEGOTIABLE EXECUTION RULES

This document is both:

- a technical implementation specification; and
- a durable checkpoint/tracker for interrupted AI-agent sessions.

The coding agent MUST read this document before modifying the repository.

The coding agent MUST inspect the real repository before implementing any task.

The coding agent MUST NOT assume that a task is incomplete merely because this plan says `TODO`, and MUST NOT assume a task is complete merely because another document says `DONE`.

Every task must be verified against actual code, tests, runtime behavior, and Git state.

## 0.1 Session recovery protocol

At the beginning of every new AI session:

```text
1. Read this file.
2. Read MASTER PROGRESS STATE.
3. Read EXECUTION LEDGER.
4. Run git status.
5. Run git log --oneline -20.
6. Run git diff.
7. Inspect the last completed task.
8. Verify its evidence.
9. Run the relevant tests.
10. Continue from NEXT ACTION.
```

Do NOT blindly continue from the previous agent's note.

If repository state and tracker disagree:

```text
STOP
↓
Inspect code
↓
Inspect tests
↓
Determine actual state
↓
Correct tracker
↓
Record reconciliation note
↓
Continue
```

## 0.2 Work phase-by-phase

Never attempt the entire transformation in one edit.

Required order:

```text
Phase 0  Baseline + repository reconciliation
    ↓
Phase 1  Target architecture + runtime mode policy
    ↓
Phase 2  Legacy-agent isolation/removal
    ↓
Phase 3  User profile + separate mode histories
    ↓
Phase 4  Chemistry domain model + curriculum
    ↓
Phase 5  NCERT RAG foundation
    ↓
Phase 6  Chemistry tutoring engine
    ↓
Phase 7  Assessment engine
    ↓
Phase 8  General Assistant
    ↓
Phase 9  Two-screen UI integration
    ↓
Phase 10 Qwen model/training integration
    ↓
Phase 11 Security + failure handling + controlled web research
    ↓
Phase 12 Performance + regression testing
    ↓
Phase 13 Documentation + release readiness
```

A phase may be split into smaller implementation commits.

Do not mark a phase `DONE` without evidence.

---

# 1. PRODUCT DEFINITION

## 1.1 Final product

Gayatri is no longer a generic multi-agent platform.

The intended runtime architecture is:

```text
                         GAYATRI
                            |
             +--------------+--------------+
             |                             |
             v                             v
      CHEMISTRY TUTOR               GENERAL ASSISTANT
             |                             |
       Tutor Runtime                  Assistant Runtime
             |                             |
       +-----+------+              +-------+-------+
       |            |              |       |       |
       v            v              v       v       v
      RAG         Qwen           Chat    Write   Summarize
       |          2.5*            |
       |            |              |
       +------+-----+              |
              |                    |
        Adaptive Tutor             |
        State Machine              |
              |                    |
              v                    |
        Student Progress           |
              |                    |
              +---------+----------+
                        |
                 User Profile
```

`*` The exact Qwen2.5 checkpoint must be recorded explicitly. Do not invent a model identifier.

## 1.2 Two user-facing screens

The application must have two distinct entry screens/workspaces.

### Chemistry Tutor

Purpose:

- teach NCERT/CBSE-oriented Chemistry;
- explain concepts;
- solve and teach numericals;
- explain reactions;
- generate and conduct practice;
- conduct assessments;
- evaluate student responses;
- identify misconceptions;
- adapt difficulty;
- track chemistry learning progress.

Core teaching cycle:

```text
Student asks / starts topic
        ↓
Determine topic + learning intent
        ↓
Retrieve relevant NCERT material
        ↓
Explain concept
        ↓
Give example
        ↓
Ask learner a question
        ↓
Evaluate response
        ↓
Detect mastery / misconception
        ↓
Adapt difficulty
        ↓
Continue / remediate / advance
        ↓
Practice
        ↓
Assessment
        ↓
Update mastery
```

### General Assistant

Purpose:

- normal conversation;
- writing;
- summarization;
- brainstorming;
- ordinary general assistance.

General Assistant is NOT a router to legacy agents.

It is a mode, not a parent orchestrator for other hidden agents.

---

# 2. CURRENT REPOSITORY FACTS TO RECONCILE

The current repository describes itself as a local-first agentic AI platform with a central local LLM routing requests to specialized agents, including examples such as Code Reviewer, Math Tutor, and General Assistant.

Current documented stack includes:

- PySide6
- QWebEngine
- QWebChannel
- llama-cpp-python / GGUF
- SQLite
- sqlite-vec
- Windows DPAPI
- pytest
- pytest-qt
- ruff
- QLoRA through Unsloth

The repository currently contains:

```text
.github/workflows/
app/
core/
docs/
scripts/
tests/
training/
```

The README documents:

```text
training/generate_data.py
training/colab_notebook.py
models deployment
```

The existing performance refactor plan identifies important implementation areas such as:

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

The coding agent must verify these paths and discover replacements if the repository has moved them.

## 2.1 Important existing-plan inconsistency

The repository's existing performance execution plan contains a contradictory state:

- its progress section declares the performance refactor `DONE`;
- the execution ledger still lists multiple `TODO` tasks.

This MUST NOT be copied into the new project tracker.

Phase 0 must reconcile the actual state and document the result.

---

# 3. MASTER PROGRESS STATE

Update this block after every meaningful task or session.

```yaml
project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 11
current_task: "P11-T01"

last_completed_task: "P10-T08 (Prompt Contracts & Inference Service Abstraction)"
last_verified_commit: "Phase 10 done"

last_test_status: "289 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P11-T01: Controlled Web Research Fallback Policy"

last_agent_note: "Phase 10 complete. Externalized versioned prompt contracts (chemistry_tutor_system_v1.txt, general_assistant_system_v1.txt), built PromptContractLoader, and unified inference routing via InferenceService."

updated_at: "2026-09-19T01:02:00+05:30"
```

## Allowed status vocabulary

Use ONLY:

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
mostly done
probably fixed
looks good
should work
```

---

# 4. MASTER ARCHITECTURE PRINCIPLES

## 4.1 No multi-agent routing in the target runtime

The final active registry must contain only:

```python
ENABLED_MODES = {
    "chemistry_tutor",
    "general_assistant",
}
```

Legacy agents may remain physically present until explicitly archived/removed, but they cannot be active runtime providers.

## 4.2 No UI-only disabling

Hiding an agent button is NOT sufficient.

Access must be blocked at:

```text
UI
↓
Bridge/API
↓
Mode validation
↓
Agent registry
↓
Runtime
↓
Provider
```

A request such as:

```text
agent=math
agent=code_review
agent=research
```

must be rejected before the legacy agent can execute.

## 4.3 No prompt-based security boundary

Do not rely on:

```text
"You are not allowed to be a coding agent"
```

as the only restriction.

The application architecture itself must prevent unavailable capabilities.

## 4.4 One model service

Do not create separate model loaders for every mode.

Target:

```text
Application
    ↓
InferenceService
    ↓
Qwen model
```

Chemistry and General Assistant provide different system policies and context.

## 4.5 Separate histories

User profile is shared.

Conversation histories are mode-specific.

```text
User
 |
 +-- Profile
 |
 +-- Chemistry workspace
 |      |
 |      +-- sessions
 |      +-- messages
 |      +-- mastery
 |      +-- assessments
 |      +-- misconceptions
 |
 +-- General workspace
        |
        +-- sessions
        +-- messages
```

Do not mix Chemistry history into General Assistant prompts and do not mix General Assistant history into the Chemistry Tutor's learning state.

---

# 5. PHASE 0 — REPOSITORY RECONNAISSANCE AND BASELINE

## Objective

Understand exactly what exists before changing architecture.

### P0-T01 — Git and environment baseline

Tasks:

- inspect branch;
- inspect working tree;
- inspect last 20 commits;
- record Python version;
- record OS;
- record installed package versions;
- inspect model availability;
- inspect database state;
- inspect environment/config files;
- verify whether secrets exist in tracked files.

Commands:

```text
git status
git branch --show-current
git log --oneline -20
python --version
pip list
```

Acceptance:

- environment recorded in docs or tracker;
- no uncommitted user work overwritten;
- baseline commit identified.

---

### P0-T02 — Repository structure inventory

Inspect:

```text
app/
core/
training/
tests/
scripts/
docs/
.github/
```

At minimum inspect current equivalents of:

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

Search the entire repository for:

```text
agent
orchestrator
router
tutor
practice
code review
math
general assistant
provider
stream
chat
generate
process
sqlite
sqlite-vec
RAG
embedding
learning
assessment
```

Create/update:

```text
docs/REPOSITORY_ARCHITECTURE_CURRENT.md
```

---

### P0-T03 — LLM call graph

Create:

```text
docs/LLM_CALL_GRAPH.md
```

Required table:

| Component | Function | Provider | Blocking | Streaming | User visible | Mode |
|---|---|---|---|---|---|---|

Every LLM invocation must appear.

Search for:

```text
LocalProvider
chat(
chat_stream(
stream(
generate(
create_completion(
create_chat_completion(
process(
```

---

### P0-T04 — Agent inventory

Create:

```text
docs/LEGACY_AGENT_INVENTORY.md
```

Table:

| Legacy agent | File/class | Current entry point | Runtime reachable? | UI reachable? | API reachable? | Dependencies | Target action |
|---|---|---|---|---|---|---|---|

Include every specialized agent discovered.

---

### P0-T05 — Baseline functional tests

Run the complete existing suite.

Record:

```text
command
environment
passed
failed
skipped
errors
warnings
```

Do not "fix" unrelated tests yet.

---

### P0-T06 — Baseline streaming/performance

Use the existing performance infrastructure where useful.

Measure at minimum:

- model load time;
- cold TTFT;
- warm TTFT;
- generation time;
- tokens/sec if available;
- memory use;
- UI responsiveness;
- cancellation latency.

Use chemistry prompts rather than the old coding/math examples for the new benchmark set.

---

### P0-T07 — Reconcile old V4 performance tracker

Inspect:

```text
Gayatri_Tutor_V4_Performance_Refactor_EXECUTION_PLAN.md
PERFORMANCE_REFACTOR_V4.md
```

For every claimed completed item:

- verify implementation;
- verify tests;
- classify as DONE, TODO, FAILED, BLOCKED or DEFERRED.

Do not carry forward stale completion claims.

---

### Phase 0 exit criteria

All must be true:

- [ ] Current architecture documented.
- [ ] Every agent inventoried.
- [ ] Every LLM path identified.
- [ ] Baseline tests recorded.
- [ ] Baseline performance recorded.
- [ ] Old performance-plan inconsistencies documented.
- [ ] Tracker updated.

---

# 6. PHASE 1 — TARGET ARCHITECTURE AND MODE POLICY

## Objective

Replace "agent selection" as a product concept with two explicit application modes.

## P1-T01 — Define canonical mode enum

Create one canonical representation, for example:

```python
class AppMode(str, Enum):
    CHEMISTRY_TUTOR = "chemistry_tutor"
    GENERAL_ASSISTANT = "general_assistant"
```

Do not duplicate mode strings across the project.

---

## P1-T02 — Central mode policy

Create a single policy object/module that defines:

```text
mode identity
allowed capabilities
system prompt policy
history scope
RAG policy
web policy
assessment availability
student-state availability
```

Example conceptual policy:

```yaml
chemistry_tutor:
  chemistry_only: true
  rag: true
  assessment: true
  adaptive_learning: true
  controlled_web_fallback: true

general_assistant:
  chemistry_tutor: false
  assessment: false
  adaptive_learning: false
  rag: false
  controlled_web_fallback: false
```

Adapt the final policy after inspecting current infrastructure.

---

## P1-T03 — Replace general-purpose routing

Current:

```text
central LLM decides which specialized agent to use
```

Target:

```text
User chooses mode
        ↓
Mode validated
        ↓
Mode runtime
        ↓
Inference
```

Do NOT ask an LLM to decide whether to invoke the legacy agents.

The model can perform intent/topic analysis *inside Chemistry Tutor*, but it cannot select hidden legacy agents.

---

## P1-T04 — Canonical runtime dispatch

Create a small deterministic dispatcher:

```text
request
 ↓
validate mode
 ↓
switch:
   chemistry_tutor -> ChemistryTutorRuntime
   general_assistant -> GeneralAssistantRuntime
otherwise:
   reject
```

Unknown values must fail closed.

---

### Phase 1 acceptance

The following must be provably true:

```text
chemistry_tutor → ChemistryTutorRuntime
general_assistant → GeneralAssistantRuntime
math → rejected
coding → rejected
code_review → rejected
research_agent → rejected
unknown → rejected
```

---

# 7. PHASE 2 — LEGACY AGENT ISOLATION / REMOVAL

## Objective

Remove old agents from the active product without destroying potentially reusable infrastructure.

## P2-T01 — Disable old agent registration

Remove legacy agents from active registration.

No code path should automatically register them.

Feature flags may exist for archival/development purposes, but default must be:

```text
legacy agents = OFF
```

---

## P2-T02 — Legacy feature flags

Centralize flags, e.g.:

```yaml
features:
  chemistry_tutor: true
  general_assistant: true

  legacy_math: false
  legacy_code_review: false
  legacy_research: false
  legacy_other: false
```

The production/default configuration must keep every legacy flag false.

---

## P2-T03 — Block direct invocation

Even if a developer attempts:

```python
runtime.run("math", ...)
```

the request must fail before model execution.

Add explicit tests.

---

## P2-T04 — Remove old UI entry points

Remove or hide:

- Math
- Code Review
- Practice-as-a-separate-agent
- Research agent selectors
- agent selector dropdowns
- agent-specific settings that no longer apply

Do not leave dead buttons.

---

## P2-T05 — Remove old prompts from active prompt loading

Legacy prompts must not be included in active runtime prompt discovery.

Do not allow prompt directory scanning to accidentally activate archived agents.

---

## P2-T06 — Archive legacy implementation

Preferred structure:

```text
legacy/
  agents/
  prompts/
```

OR keep existing files in place if moving them causes unnecessary breakage, but clearly mark them inactive.

Do not delete reusable infrastructure merely because a legacy agent is disabled.

---

## P2-T07 — Search for hidden routes

Search for:

```text
math
code_review
code reviewer
practice_agent
research_agent
agent_name
agent_type
agent_id
default_agent
fallback_agent
```

Audit:

- Python;
- JS;
- HTML;
- configs;
- tests;
- docs;
- environment files.

---

### Phase 2 security acceptance

Automated tests must prove:

```text
No legacy agent is reachable from UI.
No legacy agent is reachable through bridge.
No legacy agent is reachable through runtime dispatch.
No legacy agent is reachable through direct API arguments.
No fallback can silently select a legacy agent.
```

---

# 8. PHASE 3 — USER PROFILE AND SEPARATE MODE HISTORY

## Objective

Build the data layer for a local-first single-user application that can later become multi-user.

## P3-T01 — User identity abstraction

Even if only one local user exists initially, introduce an internal `user_id`.

Do not hard-code:

```text
user_id = 1
```

throughout the code.

---

## P3-T02 — User profile

Minimum profile fields:

```text
user_id
display_name
education_level
class/grade
board
preferred_language
created_at
updated_at
```

Chemistry-specific profile settings may include:

```text
chemistry_level
target_class
preferred_difficulty
```

---

## P3-T03 — Mode-scoped conversations

Conversation/session table needs a mode dimension.

Concept:

```text
session_id
user_id
mode
title
created_at
updated_at
```

Message table:

```text
message_id
session_id
role
content
created_at
metadata_json
```

`mode` must be constrained to:

```text
chemistry_tutor
general_assistant
```

---

## P3-T04 — Chemistry learning state

Create a separate persistence layer for:

```text
topic mastery
concept mastery
attempt count
correct count
incorrect count
difficulty exposure
last reviewed
misconceptions
confidence estimate
```

Keep this separate from generic conversation history.

---

## P3-T05 — Assessment records

Store:

```text
assessment_id
user_id
topic
chapter
assessment_type
difficulty
questions
answers
score
started_at
completed_at
```

Do not put full assessment state in a chat prompt.

---

## P3-T06 — Migration

Create migration logic for existing sessions.

Existing historical data must not be silently mixed into the new Chemistry Tutor context.

Possible treatment:

```text
legacy session
   ↓
preserve
   ↓
mode = legacy / archived
   ↓
not used for active model context
```

---

### Phase 3 acceptance

Verify:

- Chemistry history is visible only inside Chemistry mode.
- General history is visible only inside General Assistant.
- User profile is shared.
- Chemistry mastery is never updated by General Assistant messages.
- General Assistant cannot mutate Chemistry assessment state.

---

# 9. PHASE 4 — CHEMISTRY DOMAIN MODEL AND NCERT/CBSE CURRICULUM

## Objective

Make Chemistry a real domain product rather than a prompt wrapper.

## P4-T01 — Define curriculum metadata

Create a curriculum manifest, for example:

```text
data/curriculum/chemistry/
  curriculum.yaml
```

The exact location should follow repository conventions.

Metadata should support:

```text
board
class
subject
chapter
unit
topic
subtopic
learning_outcome
prerequisite
difficulty
source_reference
```

---

## P4-T02 — Topic taxonomy

Create a structured chemistry topic taxonomy covering the supported NCERT/CBSE scope.

Do not invent a "complete NCERT syllabus" from memory.

The curriculum manifest must be populated from the actual approved source material supplied to the project.

---

## P4-T03 — Prerequisite relationships

Represent dependencies such as:

```text
Mole Concept
   ↓
Stoichiometry
   ↓
Chemical Equations
   ↓
Chemical Reactions
```

Do not hard-code a large learning graph in prompts.

Use structured metadata.

---

## P4-T04 — Chemistry question taxonomy

Create types:

```text
conceptual
definition
explanation
worked_example
numerical
reaction_prediction
reaction_completion
equation_balancing
assertion_reasoning
mcq
short_answer
long_answer
previous_year_style
chapter_test
mock_test
adaptive_practice
```

---

## P4-T05 — Difficulty taxonomy

Define deterministic levels such as:

```text
L1 = recall
L2 = basic understanding
L3 = application
L4 = multi-step application
L5 = integrated reasoning
```

Do not present these labels to the student unless UI explicitly needs them.

---

### Phase 4 acceptance

- Curriculum metadata is machine-readable.
- Topic names have stable IDs.
- Prerequisites can be queried.
- Assessment types have stable IDs.
- Chemistry prompts can reference topic IDs rather than fragile text names.

---

# 10. PHASE 5 — NCERT RAG FOUNDATION

## Objective

Build the authoritative chemistry knowledge layer.

Target:

```text
Approved NCERT material
        ↓
Document validation
        ↓
Text extraction
        ↓
Cleaning/normalization
        ↓
Chunking
        ↓
Metadata tagging
        ↓
Embeddings
        ↓
Vector index
        ↓
Retriever
        ↓
Relevant NCERT evidence
        ↓
Qwen
```

## P5-T01 — Source manifest

Create a manifest containing for each source:

```text
source_id
title
class
chapter
source_type
version/date if known
file path
checksum
license/usage note
```

Do not silently ingest arbitrary Internet material as "NCERT".

---

## P5-T02 — Document ingestion

Support the approved document format(s) already suitable for the repo.

Processing must be deterministic.

Record:

```text
source_id
document_hash
parser
page/chapter
chunk_count
ingestion_time
```

---

## P5-T03 — Chunk schema

Each chunk should preserve:

```text
chunk_id
source_id
chapter
topic
subtopic
page/reference
text
embedding_id
```

This enables citations and debugging.

---

## P5-T04 — Retrieval

Implement:

```text
query
 ↓
query normalization
 ↓
embedding
 ↓
vector retrieval
 ↓
optional keyword/lexical filter
 ↓
top-k
 ↓
quality threshold
 ↓
context pack
```

Keep retrieval deterministic and testable.

---

## P5-T05 — Retrieval confidence

Introduce a retrieval confidence/quality signal.

Do NOT treat "top-k exists" as proof that the retrieved context is relevant.

Pseudo-policy:

```text
high confidence
  → use NCERT evidence

medium confidence
  → use NCERT evidence cautiously + model reasoning

low confidence
  → controlled research fallback OR explicit uncertainty
```

Exact thresholds must be measured experimentally and stored in configuration.

---

## P5-T06 — Citations

Chemistry responses based on RAG should be able to identify source references such as:

```text
NCERT Chemistry
Class X
Chapter Y
Page/reference Z
```

Do not fabricate page numbers.

Only cite metadata actually present in the ingested source.

---

## P5-T07 — RAG evaluation set

Create a small golden set:

```text
question
expected topic
expected source/chapter
retrieval expected
answer notes
```

Start with manually verified questions.

---

# 11. PHASE 6 — CHEMISTRY TUTOR ENGINE

## Objective

Implement actual tutoring behavior.

The Chemistry Tutor is one runtime, not a collection of hidden agents.

## P6-T01 — Tutor state machine

Define explicit states:

```text
IDLE
DISCOVERING
EXPLAINING
EXAMPLE
CHECKING
EVALUATING
REMEDIATING
PRACTICING
ASSESSING
COMPLETED
```

The exact implementation may differ, but state transitions must be explicit and testable.

---

## P6-T02 — Intent classification inside tutor

Supported intents:

```text
learn
explain
solve
practice
test
review
clarify
summarize
compare
```

Do not route to another agent.

---

## P6-T03 — Student-level adaptation

Use user profile plus observed performance.

Inputs:

```text
class/grade
board
topic
prior mastery
recent errors
current answer
requested difficulty
```

Output:

```text
response depth
terminology
number of examples
question difficulty
amount of scaffolding
```

---

## P6-T04 — Explanation policy

A concept explanation should generally support:

```text
1. direct explanation
2. intuition
3. chemistry-specific example
4. worked example when useful
5. student check
```

Do not force the exact format every time.

The tutor must adapt to the student's request.

---

## P6-T05 — Numerical-solving mode

Numerical tutoring should teach the method.

Target structure:

```text
Given
↓
Find
↓
Formula/principle
↓
Substitution
↓
Calculation
↓
Unit check
↓
Final answer
↓
Concept check
```

The tutor should avoid merely dumping a final number when the learner is in teaching mode.

---

## P6-T06 — Reaction mode

Support:

- identifying reactants/products;
- balancing equations;
- explaining reaction conditions;
- explaining why the reaction occurs when supported by evidence/model knowledge;
- detecting incorrect student reactions;
- stepwise correction.

Do not invent reactions or conditions when uncertain.

---

## P6-T07 — Student answer evaluator

Evaluation must produce structured internal state:

```text
correctness
confidence
concept_understanding
error_type
misconception
next_difficulty
recommended_action
```

Do not store hidden model chain-of-thought.

Persist only concise evaluation metadata.

---

## P6-T08 — Difficulty adaptation

Example policy:

```text
correct + confident
    → maintain or increase difficulty

correct + uncertain
    → same level + reinforcement

partially correct
    → targeted hint/remediation

incorrect
    → diagnose misconception + simpler example

repeated incorrect
    → prerequisite review
```

Do not use arbitrary difficulty jumps.

---

## P6-T09 — Tutor memory policy

The tutor may remember:

```text
current topic
recent attempts
mastery estimate
known misconceptions
preferred explanation level
recent weak concepts
```

Avoid dumping entire conversation history into every prompt.

---

## P6-T10 — Out-of-domain handling

Chemistry Tutor should detect obvious non-chemistry requests.

Example:

```text
"write Python code"
```

Response should redirect the user to General Assistant rather than invoking a coding agent.

The tutor must not become a hidden coding agent.

---

### Phase 6 acceptance

A test session must demonstrate:

```text
Question
→ explanation
→ example
→ question to student
→ student answer
→ evaluation
→ adaptation
→ next question
```

and prove the model does not silently call a legacy agent.

---

# 12. PHASE 7 — ASSESSMENT ENGINE

## Objective

Create a reusable, deterministic assessment subsystem inside Chemistry Tutor.

## P7-T01 — Question schema

Create a stable question schema supporting:

```json
{
  "question_id": "",
  "topic_id": "",
  "type": "mcq",
  "difficulty": 1,
  "question": "",
  "options": [],
  "correct_answer": "",
  "explanation": "",
  "source_id": "",
  "source_reference": "",
  "grading_notes": {}
}
```

Never force every question type into one fragile schema if a better typed model exists.

---

## P7-T02 — MCQs

Support:

- single correct;
- distractors;
- explanation;
- topic;
- difficulty;
- source metadata.

---

## P7-T03 — Numerical problems

Support:

- numerical answer;
- optional tolerance;
- expected unit;
- solution steps;
- grading feedback.

---

## P7-T04 — Assertion/reasoning

Support:

- assertion;
- reason;
- answer options;
- explanation.

---

## P7-T05 — Reaction completion

Support:

```text
reactants
→ blank/product/condition
→ learner answer
→ evaluation
```

---

## P7-T06 — Equation balancing

Support both:

```text
student types coefficients
```

and, later if useful:

```text
structured coefficient inputs
```

Use deterministic balancing checks where possible instead of trusting an LLM evaluation for basic arithmetic correctness.

---

## P7-T07 — Chapter tests

Test generation should be driven by topic metadata.

Control:

```text
chapter
question count
difficulty mix
question types
time limit
```

---

## P7-T08 — Full mock tests

Support a configurable chemistry test spanning multiple chapters.

Do not hard-code one fixed test.

---

## P7-T09 — Adaptive tests

Adaptive difficulty must use actual performance signals.

Minimum:

```text
topic mastery
recent answer correctness
difficulty history
```

---

## P7-T10 — Assessment anti-leakage

Do not expose the answer key in frontend state before submission.

Do not send hidden answer keys through insecure bridge messages if avoidable.

Keep grading authoritative on the backend/runtime side.

---

# 13. PHASE 8 — GENERAL ASSISTANT

## Objective

Create a clean, simple general-purpose assistant without legacy agent routing.

Supported initial capabilities:

```text
normal conversation
writing
summarization
brainstorming
general reasoning
```

## P8-T01 — General system policy

General Assistant should:

- be helpful;
- remain local-first;
- not claim unavailable capabilities;
- avoid pretending to be the Chemistry Tutor;
- not mutate chemistry mastery;
- not create chemistry assessments through hidden routing.

---

## P8-T02 — Writing mode

Normal chat may include:

```text
rewrite
draft
polish
shorten
expand
professionalize
brainstorm
```

No separate writing agent is needed.

---

## P8-T03 — Summarization

Provide summarization through the General Assistant itself.

Support text/context already available in the app.

Later file ingestion can be added without creating another agent.

---

## P8-T04 — Brainstorming

Support:

```text
ideas
outlines
alternatives
pros/cons
creative generation
planning
```

Avoid automatic mode switching.

---

## P8-T05 — Chemistry boundary

If a chemistry teaching request arrives in General Assistant, provide a concise redirect:

```text
"This is better handled in Chemistry Tutor. Open Chemistry Tutor to continue."
```

Do not call Chemistry Tutor internally.

---

# 14. PHASE 9 — TWO-SCREEN UI

## Objective

Make the product visibly match the new architecture.

## Target navigation

```text
                 GAYATRI
                    |
          +---------+---------+
          |                   |
          v                   v
   Chemistry Tutor     General Assistant
```

No agent dropdown.

No legacy-agent cards.

No hidden "choose agent" UX.

---

## P9-T01 — Landing/home screen

Provide two clear choices:

```text
Chemistry Tutor
Learn Chemistry with guided, adaptive teaching.

General Assistant
Chat, write, summarize, and brainstorm.
```

---

## P9-T02 — Chemistry workspace

Recommended sections:

```text
Header
Topic/context indicator
Conversation
Tutor interaction
Answer/check area
Optional progress summary
Input area
```

Do not overload the first version with dashboards.

---

## P9-T03 — General Assistant workspace

Keep it simpler:

```text
Conversation history
Chat
Input
New conversation
```

---

## P9-T04 — Separate history navigation

Chemistry history list:

```text
Chemistry sessions only
```

General history list:

```text
General sessions only
```

---

## P9-T05 — Empty states

Test first-run behavior.

Examples:

```text
No chemistry sessions yet
Start a topic or ask a chemistry question.
```

```text
No general conversations yet
Start a conversation.
```

---

## P9-T06 — Errors

Errors must explain:

- model unavailable;
- database unavailable;
- RAG unavailable;
- web fallback unavailable;
- request cancelled.

Do not expose stack traces to normal users.

---

## P9-T07 — Streaming UI

Preserve the existing streaming approach where it is healthy.

The visible path should remain:

```text
User
 ↓
Bridge
 ↓
Active mode runtime
 ↓
Inference
 ↓
stream chunks
 ↓
UI
```

No hidden full-response blocking stage should delay first token unnecessarily.

---

# 15. PHASE 10 — QWEN MODEL + TRAINING INTEGRATION

## Objective

Prepare the repository for a Chemistry-specialized Qwen fine-tuning workflow.

## Important model naming note

Do not hard-code the phrase "Qwen2.5 1B" as an exact checkpoint identifier.

The Qwen2.5 model family includes sizes such as 0.5B and 1.5B; therefore the exact model checkpoint must be recorded explicitly before training/integration.

Example configuration concept:

```yaml
model:
  provider: local
  family: qwen2.5
  model_id: "<exact-checkpoint>"
  quantization: "<exact-quantization>"
```

The agent must not silently choose a different model.

---

## P10-T01 — Model abstraction

Ensure both modes can use the same `InferenceService`.

```text
ChemistryTutorRuntime
      \
       → InferenceService → Qwen
      /
GeneralAssistantRuntime
```

---

## P10-T02 — Prompt contract

Create versioned system prompts.

Suggested:

```text
training/prompts/
  chemistry_tutor_system_v1.txt
  general_assistant_system_v1.txt
```

Exact location may follow existing conventions.

Do not hard-code large prompts across Python files.

---

## P10-T03 — Training data contract

Create a training-data specification before generating data.

Each example should capture appropriate fields such as:

```text
instruction
input/context
expected behavior
response
topic metadata
difficulty
interaction stage
assessment type
```

Training examples must emphasize tutor behavior rather than memorizing textbook paragraphs.

---

## P10-T04 — Chemistry training categories

Plan dataset categories:

```text
A. Concept explanation
B. Socratic questioning
C. Worked examples
D. Numerical tutoring
E. Reaction explanation
F. Equation balancing
G. MCQ generation
H. Numerical question generation
I. Assertion/reasoning
J. Student-answer evaluation
K. Misconception diagnosis
L. Difficulty adaptation
M. Chapter revision
N. Test feedback
O. Out-of-domain boundary behavior
P. RAG-aware answering
Q. Uncertainty / source limitation behavior
```

---

## P10-T05 — Do not fabricate training corpus now

The repository should contain:

- schema;
- generation tooling;
- validation;
- dataset split tooling;
- training config;

but the agent must not invent a large "official NCERT dataset".

The actual training corpus will be generated and reviewed later.

---

## P10-T06 — Data validation

Before training:

```text
schema validation
duplicate detection
empty-response detection
topic validation
difficulty validation
unsafe content scan
format validation
train/validation split
leakage checks
```

---

## P10-T07 — Fine-tuning pipeline

Reuse the current QLoRA/Unsloth workflow where appropriate.

The pipeline must support:

```text
dataset
 ↓
validation
 ↓
train/validation split
 ↓
QLoRA training
 ↓
evaluation
 ↓
adapter checkpoint
 ↓
merge/convert if required
 ↓
GGUF
 ↓
local inference verification
```

Do not alter training hyperparameters solely because another model was used previously.

---

## P10-T08 — Model evaluation

Create an evaluation set that is NEVER used for training.

Measure at minimum:

```text
instruction adherence
chemistry correctness
teaching behavior
student-answer evaluation
numerical reasoning
reaction accuracy
RAG faithfulness
out-of-domain behavior
```

---

# 16. PHASE 11 — CONTROLLED WEB RESEARCH FALLBACK

## Objective

Allow carefully bounded research without turning the application back into an unrestricted research-agent system.

## P11-T01 — Web policy

Network use must be explicit and policy-controlled.

Recommended default:

```text
local inference = ON
web research = OFF unless policy allows it
```

---

## P11-T02 — Chemistry fallback conditions

Controlled research may be considered when:

```text
RAG evidence is insufficient
AND
question requires information not found in approved material
AND
web use is allowed by configuration
```

It may also be triggered by explicit user request where supported.

---

## P11-T03 — No arbitrary agent creation

Web research is a capability of the active runtime, not a "Research Agent".

Do not restore the old multi-agent design.

---

## P11-T04 — Source handling

For web-derived chemistry information:

```text
query
 ↓
search
 ↓
source selection
 ↓
content extraction
 ↓
source metadata
 ↓
context
 ↓
answer
```

Keep source URLs/titles in response metadata where UI supports citations.

---

## P11-T05 — Prompt injection defense

Treat retrieved web content as untrusted data.

Retrieved pages must never be able to redefine:

- system policy;
- active mode;
- tool permissions;
- available agents;
- application configuration.

---

## P11-T06 — Network failure

If web fallback fails:

```text
do not crash
do not pretend web research occurred
answer from available evidence OR state uncertainty
```

---

# 17. PHASE 12 — SECURITY, FAILURE HANDLING, AND PERFORMANCE

## P12-T01 — Security audit

Search for:

```text
API keys
tokens
passwords
database credentials
hard-coded URLs with secrets
unsafe subprocess use
path traversal
arbitrary file read
unsafe deserialization
SQL injection
unsafe SQL formatting
shell injection
untrusted web content
unsafe HTML rendering
unsafe JavaScript bridge exposure
```

---

## P12-T02 — QWebChannel boundary

Audit every exposed bridge method.

Only expose methods required by:

```text
Chemistry Tutor
General Assistant
UI navigation
safe persistence
```

Do not expose a generic:

```text
execute_agent(name)
run_tool(name)
call_any_agent(...)
```

bridge API.

---

## P12-T03 — Mode validation

Validate mode on every boundary.

Example:

```python
if mode not in ACTIVE_MODES:
    raise InvalidMode(...)
```

Do this server/backend-side, not only in JavaScript.

---

## P12-T04 — Database failure handling

A model response should not be discarded solely because history persistence fails.

Target:

```text
generation
 ↓
visible response
 ↓
background persistence
```

If persistence fails:

```text
response remains visible
error logged
retry/recovery available
```

---

## P12-T05 — Cancellation

Verify:

```text
UI STOP
 ↓
bridge cancellation
 ↓
runtime cancellation
 ↓
inference cancellation
 ↓
cleanup
 ↓
UI idle
```

Requirements:

- thread-safe;
- idempotent;
- no orphan worker;
- no stale callback;
- no duplicate completion.

---

## P12-T06 — Performance metrics

Record:

```text
model load
TTFT
generation time
tokens/sec
UI render count
memory
cancellation latency
RAG retrieval time
database save time
```

Do not optimize only for speed. Preserve answer quality.

---

# 18. PHASE 13 — TESTING AND REGRESSION PROTECTION

## P13-T01 — Agent availability tests

These are mandatory.

```text
chemistry_tutor accepted
general_assistant accepted

math rejected
coding rejected
code_review rejected
practice_agent rejected
research_agent rejected
unknown rejected
```

---

## P13-T02 — UI mode tests

Verify:

- exactly two top-level modes;
- no legacy agent controls;
- correct history shown per mode;
- switching modes does not leak conversation context.

---

## P13-T03 — Chemistry tutor loop tests

Test:

```text
explanation
example
question
student answer
evaluation
adaptation
next step
```

---

## P13-T04 — Chemistry domain tests

Include:

```text
concept question
numerical
reaction question
equation balancing
MCQ
assertion/reasoning
chapter test
mock test
adaptive test
```

---

## P13-T05 — RAG tests

Verify:

```text
relevant question → relevant NCERT chunk
irrelevant question → low confidence
citation → real source metadata
missing source → no fabricated citation
RAG unavailable → controlled fallback
```

---

## P13-T06 — General Assistant tests

Verify:

```text
normal conversation
writing
summarization
brainstorming
```

And verify General Assistant does not mutate Chemistry state.

---

## P13-T07 — Boundary tests

General Assistant:

```text
chemistry teaching request
→ redirect
→ no Chemistry runtime call
```

Chemistry Tutor:

```text
coding request
→ redirect
→ no coding runtime call
```

---

## P13-T08 — Streaming tests

Required:

```text
provider yields multiple chunks
active runtime yields multiple chunks
bridge preserves chunks
UI receives chunks progressively
concatenated chunks == final response
```

No intermediate layer may silently buffer the entire answer before display.

---

## P13-T09 — Cancellation tests

Verify:

```text
start
↓
stream
↓
cancel
↓
stop generation
↓
cleanup
↓
exactly one completion state
```

---

## P13-T10 — Persistence tests

Verify:

- no duplicate message save;
- failed save does not erase visible response;
- sessions reopen correctly;
- Chemistry and General history remain isolated.

---

## P13-T11 — Long-conversation tests

Verify:

- prompt does not grow without control;
- TTFT does not degrade unexpectedly;
- Chemistry mastery state remains consistent;
- mode separation remains intact.

---

# 19. REQUIRED ARCHITECTURE DOCUMENTATION

Create/update:

```text
docs/REPOSITORY_ARCHITECTURE_CURRENT.md
docs/TARGET_ARCHITECTURE.md
docs/ACTIVE_MODES.md
docs/LEGACY_AGENT_INVENTORY.md
docs/LLM_CALL_GRAPH.md
docs/CHEMISTRY_TUTOR_BEHAVIOR.md
docs/CHEMISTRY_CURRICULUM_SCHEMA.md
docs/RAG_ARCHITECTURE.md
docs/TRAINING_DATA_SPEC.md
docs/SECURITY_MODEL.md
docs/TEST_STRATEGY.md
```

Do not duplicate contradictory architecture definitions across documents.

`TARGET_ARCHITECTURE.md` should be the source of truth for the final product architecture.

---

# 20. RECOMMENDED TARGET MODULE ORGANIZATION

Do NOT blindly create this structure. First map the current repository and reuse existing modules.

Conceptual target:

```text
app/
  ui/
    chemistry/
    general/
    shared/
  bridge/

core/
  modes/
    chemistry_tutor.py
    general_assistant.py
    policy.py

  inference/
    service.py

  chemistry/
    curriculum.py
    tutor_engine.py
    evaluator.py
    difficulty.py
    assessments.py
    progress.py

  rag/
    ingestion.py
    retrieval.py
    citations.py
    policy.py

  history/
    sessions.py
    messages.py

  user/
    profile.py

  legacy/
    ...

training/
  schemas/
  datasets/
  prompts/
  validation/
  train/
  evaluation/
```

The actual repository structure should be chosen based on current code.

Avoid unnecessary moves solely for aesthetics.

---

# 21. CONFIGURATION MODEL

Use centralized configuration.

Conceptual example:

```yaml
app:
  default_mode: chemistry_tutor

modes:
  chemistry_tutor:
    enabled: true
    rag_enabled: true
    assessments_enabled: true
    adaptive_learning_enabled: true
    web_fallback_enabled: true

  general_assistant:
    enabled: true
    rag_enabled: false
    assessments_enabled: false
    adaptive_learning_enabled: false
    web_fallback_enabled: false

legacy:
  enabled: false
  math: false
  coding: false
  code_review: false
  research: false

model:
  provider: local
  model_id: ""
  backend: llama_cpp
  quantization: ""

rag:
  enabled: true
  top_k: 5
  minimum_confidence: ""

web:
  enabled: false
  controlled_fallback_only: true

persistence:
  backend: sqlite
```

Actual keys must match the existing project's configuration system.

---

# 22. TRACKER RULES

## Every task row must contain

```text
ID
Phase
Task
Status
Started
Evidence
Tests
Benchmark
Files Changed
Commit
Agent Note
```

Recommended ledger:

| ID | Phase | Task | Status | Evidence | Tests | Benchmark | Files Changed | Commit |
|---|---:|---|---|---|---|---|---|---|

## Evidence requirements

Good:

```text
P2-T03 DONE
Evidence:
Direct runtime invocation with mode="math" raises InvalidMode
before provider invocation.

Tests:
tests/test_active_modes.py::test_legacy_modes_rejected
PASSED
```

Bad:

```text
P2-T03 DONE
Evidence:
Old agents removed.
```

---

# 23. FAILURE / BLOCKED PROTOCOL

When blocked, update:

```yaml
status: BLOCKED
blocker: ""
evidence: ""
attempted: ""
required: ""
workaround: ""
```

Do not silently skip the task.

If the task is no longer relevant:

```yaml
status: DEFERRED
reason: ""
replacement: ""
```

If implementation caused a regression:

```yaml
status: FAILED
failure: ""
reproduction: ""
rollback_or_fix: ""
```

---

# 24. COMMIT STRATEGY

Prefer small, coherent commits.

Recommended sequence:

```text
refactor: establish chemistry/general baseline
refactor: define active application modes
security: block legacy agent dispatch
refactor: isolate legacy agent implementations
feat: add mode-scoped persistence
feat: add chemistry curriculum model
feat: add NCERT ingestion pipeline
feat: add chemistry retrieval
feat: add chemistry tutor state machine
feat: add student answer evaluation
feat: add adaptive difficulty
feat: add chemistry assessment engine
feat: add general assistant mode
feat: split chemistry and general UI
feat: integrate Qwen model configuration
feat: add training data schema
security: add controlled web research policy
test: add active mode isolation tests
test: add chemistry tutor regression suite
perf: benchmark chemistry runtime
docs: finalize chemistry/general architecture
```

Do not create giant commits containing the entire migration.

---

# 25. DEFINITION OF DONE — PRODUCT LEVEL

The transformation is complete only when ALL of the following are true.

## Runtime

```text
[ ] Application launches locally.
[ ] Only two active modes exist.
[ ] Chemistry Tutor works.
[ ] General Assistant works.
[ ] Legacy agents cannot be invoked.
[ ] No hidden fallback selects legacy agents.
```

## Chemistry

```text
[ ] NCERT/CBSE-oriented content model exists.
[ ] NCERT RAG works.
[ ] RAG citations are real.
[ ] Model knowledge can supplement RAG.
[ ] Controlled web fallback works according to policy.
[ ] Tutor explains concepts.
[ ] Tutor gives examples.
[ ] Tutor asks the student questions.
[ ] Tutor evaluates answers.
[ ] Tutor adapts difficulty.
[ ] Tutor tracks chemistry progress.
[ ] Numericals work.
[ ] Reactions work.
[ ] MCQs work.
[ ] Assertion/reasoning works.
[ ] Reaction completion works.
[ ] Equation balancing works.
[ ] Chapter tests work.
[ ] Mock tests work.
[ ] Adaptive tests work.
```

## General Assistant

```text
[ ] Normal conversation works.
[ ] Writing works.
[ ] Summarization works.
[ ] Brainstorming works.
[ ] No Chemistry state mutation occurs.
```

## UI

```text
[ ] Exactly two top-level screens/modes.
[ ] No legacy agent selector.
[ ] Separate histories.
[ ] Mode boundaries visible.
[ ] Errors are handled cleanly.
[ ] Streaming remains responsive.
```

## Data

```text
[ ] User profile exists.
[ ] Chemistry history is isolated.
[ ] General history is isolated.
[ ] Chemistry mastery persists.
[ ] Assessment state persists.
[ ] Data model supports future multiple users.
```

## Security

```text
[ ] Legacy agent endpoints blocked.
[ ] QWebChannel surface audited.
[ ] No secrets committed.
[ ] Web content treated as untrusted.
[ ] Web fallback cannot alter system policy.
[ ] Assessment answer keys protected.
[ ] Database writes validated.
```

## Quality

```text
[ ] Existing relevant tests pass.
[ ] New chemistry tests pass.
[ ] Boundary tests pass.
[ ] RAG tests pass.
[ ] Streaming tests pass.
[ ] Cancellation tests pass.
[ ] Persistence tests pass.
[ ] Performance benchmark recorded.
```

---

# 26. FINAL VALIDATION SCRIPT / CHECKLIST

Before declaring release readiness:

```text
git status
git diff
git log --oneline -20
pytest
ruff check .
```

Use repository-specific equivalents where needed.

Then manually verify:

```text
1. Launch application.
2. Open Chemistry Tutor.
3. Ask a chemistry concept question.
4. Confirm NCERT retrieval.
5. Ask for a numerical.
6. Answer incorrectly.
7. Verify tutor evaluates and adapts.
8. Request an MCQ.
9. Complete it.
10. Request a chapter test.
11. Verify chemistry history is stored.
12. Switch to General Assistant.
13. Confirm chemistry history is not shown as general history.
14. Write something.
15. Summarize something.
16. Brainstorm something.
17. Try a chemistry question in General Assistant.
18. Confirm redirect without Chemistry runtime invocation.
19. Try a coding request in Chemistry Tutor.
20. Confirm redirect without coding runtime invocation.
21. Attempt direct legacy-agent invocation through available bridge/runtime APIs.
22. Confirm rejection.
23. Test cancellation.
24. Restart app.
25. Verify sessions and profile reload.
```

---

# 27. FINAL RELEASE REPORT

Before marking Phase 13 DONE, create:

```text
docs/RELEASE_READINESS_REPORT.md
```

Include:

```text
Repository commit
Python version
OS
Model identifier
Model quantization
Embedding model
RAG index version
Database schema version

Tests:
passed
failed
skipped

Benchmarks:
cold TTFT
warm TTFT
tokens/sec
memory
RAG retrieval latency
UI render metrics

Security:
legacy agent isolation
bridge audit
secret scan
web fallback audit

Known limitations
Deferred features
Next recommended work
```

---

# 28. WHAT MUST NOT HAPPEN

The AI coding agent MUST NOT:

```text
- rewrite the entire repository without first mapping it;
- remove working infrastructure merely for cleanliness;
- create more agents to implement Chemistry features;
- reintroduce a central LLM router that selects hidden agents;
- rely only on UI hiding for security;
- fabricate NCERT source citations;
- fabricate an official NCERT dataset;
- claim training has occurred without recorded training evidence;
- change models silently;
- mix Chemistry and General Assistant conversation history;
- let General Assistant mutate Chemistry mastery;
- let Chemistry Tutor invoke coding/math/research agents;
- expose answer keys to the browser unnecessarily;
- log private conversations by default;
- claim a phase is DONE without evidence;
- mark work DONE merely because code compiles;
- overwrite user changes already present in the working tree.
```

---

# 29. NEXT ACTION

The next AI session MUST begin with:

```text
P0-T01 — Git and environment baseline
```

Then complete Phase 0 before modifying the architecture.

The first deliverables should be:

```text
docs/REPOSITORY_ARCHITECTURE_CURRENT.md
docs/LLM_CALL_GRAPH.md
docs/LEGACY_AGENT_INVENTORY.md
```

and an updated MASTER PROGRESS STATE.

Do not begin Chemistry implementation until Phase 0 gives a verified picture of:

```text
current active agents
current routing
current UI
current inference path
current persistence path
current RAG implementation
current training implementation
current test baseline
```

---

# 30. CURRENT EXECUTION LEDGER

Initialize the ledger below. Update it continuously.

| ID | Phase | Task | Status | Evidence | Tests | Benchmark | Files Changed | Commit |
|---|---:|---|---|---|---|---|---|---|
| P0-T01 | 0 | Git/environment baseline | TODO | | | | | |
| P0-T02 | 0 | Repository structure inventory | TODO | | | | | |
| P0-T03 | 0 | LLM call graph | TODO | | | | | |
| P0-T04 | 0 | Legacy agent inventory | TODO | | | | | |
| P0-T05 | 0 | Existing test baseline | TODO | | | | | |
| P0-T06 | 0 | Baseline streaming/performance | TODO | | | | | |
| P0-T07 | 0 | Reconcile existing V4 performance tracker | TODO | | | | | |
| P1-T01 | 1 | Canonical application mode enum | TODO | | | | | |
| P1-T02 | 1 | Central mode policy | TODO | | | | | |
| P1-T03 | 1 | Replace general-purpose routing | TODO | | | | | |
| P1-T04 | 1 | Deterministic active-mode dispatcher | TODO | | | | | |
| P2-T01 | 2 | Disable old agent registration | TODO | | | | | |
| P2-T02 | 2 | Legacy feature flags | TODO | | | | | |
| P2-T03 | 2 | Block direct legacy invocation | TODO | | | | | |
| P2-T04 | 2 | Remove legacy UI entry points | TODO | | | | | |
| P2-T05 | 2 | Remove legacy prompts from active loading | TODO | | | | | |
| P2-T06 | 2 | Archive legacy implementations | TODO | | | | | |
| P2-T07 | 2 | Search hidden legacy routes | TODO | | | | | |
| P3-T01 | 3 | User identity abstraction | TODO | | | | | |
| P3-T02 | 3 | User profile | TODO | | | | | |
| P3-T03 | 3 | Mode-scoped conversations | TODO | | | | | |
| P3-T04 | 3 | Chemistry learning-state persistence | TODO | | | | | |
| P3-T05 | 3 | Assessment persistence | TODO | | | | | |
| P3-T06 | 3 | Existing-data migration | TODO | | | | | |
| P4-T01 | 4 | Curriculum metadata | TODO | | | | | |
| P4-T02 | 4 | Chemistry topic taxonomy | TODO | | | | | |
| P4-T03 | 4 | Prerequisite relationships | TODO | | | | | |
| P4-T04 | 4 | Chemistry question taxonomy | TODO | | | | | |
| P4-T05 | 4 | Difficulty taxonomy | TODO | | | | | |
| P5-T01 | 5 | NCERT source manifest | TODO | | | | | |
| P5-T02 | 5 | Document ingestion | TODO | | | | | |
| P5-T03 | 5 | Chemistry chunk schema | TODO | | | | | |
| P5-T04 | 5 | Retrieval pipeline | TODO | | | | | |
| P5-T05 | 5 | Retrieval confidence | TODO | | | | | |
| P5-T06 | 5 | RAG citations | TODO | | | | | |
| P5-T07 | 5 | RAG golden evaluation set | TODO | | | | | |
| P6-T01 | 6 | Tutor state machine | TODO | | | | | |
| P6-T02 | 6 | Tutor intent classification | TODO | | | | | |
| P6-T03 | 6 | Student-level adaptation | TODO | | | | | |
| P6-T04 | 6 | Explanation policy | TODO | | | | | |
| P6-T05 | 6 | Numerical tutoring | TODO | | | | | |
| P6-T06 | 6 | Reaction tutoring | TODO | | | | | |
| P6-T07 | 6 | Student-answer evaluator | TODO | | | | | |
| P6-T08 | 6 | Difficulty adaptation | TODO | | | | | |
| P6-T09 | 6 | Tutor memory policy | TODO | | | | | |
| P6-T10 | 6 | Out-of-domain boundaries | TODO | | | | | |
| P7-T01 | 7 | Question schema | TODO | | | | | |
| P7-T02 | 7 | MCQ engine | TODO | | | | | |
| P7-T03 | 7 | Numerical assessment | TODO | | | | | |
| P7-T04 | 7 | Assertion/reasoning | TODO | | | | | |
| P7-T05 | 7 | Reaction completion | TODO | | | | | |
| P7-T06 | 7 | Equation balancing | TODO | | | | | |
| P7-T07 | 7 | Chapter tests | TODO | | | | | |
| P7-T08 | 7 | Full mock tests | TODO | | | | | |
| P7-T09 | 7 | Adaptive tests | TODO | | | | | |
| P7-T10 | 7 | Assessment anti-leakage | TODO | | | | | |
| P8-T01 | 8 | General Assistant policy | TODO | | | | | |
| P8-T02 | 8 | Writing support | TODO | | | | | |
| P8-T03 | 8 | Summarization | TODO | | | | | |
| P8-T04 | 8 | Brainstorming | TODO | | | | | |
| P8-T05 | 8 | Chemistry boundary | TODO | | | | | |
| P9-T01 | 9 | Landing/home screen | TODO | | | | | |
| P9-T02 | 9 | Chemistry workspace | TODO | | | | | |
| P9-T03 | 9 | General workspace | TODO | | | | | |
| P9-T04 | 9 | Separate history navigation | TODO | | | | | |
| P9-T05 | 9 | First-run/empty states | TODO | | | | | |
| P9-T06 | 9 | UI error states | TODO | | | | | |
| P9-T07 | 9 | Streaming UI integration | TODO | | | | | |
| P10-T01 | 10 | Shared model abstraction | TODO | | | | | |
| P10-T02 | 10 | Versioned prompt contracts | TODO | | | | | |
| P10-T03 | 10 | Training-data contract | TODO | | | | | |
| P10-T04 | 10 | Chemistry training categories | TODO | | | | | |
| P10-T05 | 10 | Training pipeline scaffold | TODO | | | | | |
| P10-T06 | 10 | Training-data validation | TODO | | | | | |
| P10-T07 | 10 | QLoRA/Unsloth pipeline integration | TODO | | | | | |
| P10-T08 | 10 | Held-out model evaluation | TODO | | | | | |
| P11-T01 | 11 | Web policy | TODO | | | | | |
| P11-T02 | 11 | Chemistry research fallback | TODO | | | | | |
| P11-T03 | 11 | Capability-based web runtime | TODO | | | | | |
| P11-T04 | 11 | Web source handling | TODO | | | | | |
| P11-T05 | 11 | Retrieved-content injection defense | TODO | | | | | |
| P11-T06 | 11 | Web failure handling | TODO | | | | | |
| P12-T01 | 12 | Security audit | TODO | | | | | |
| P12-T02 | 12 | QWebChannel audit | TODO | | | | | |
| P12-T03 | 12 | Boundary validation | TODO | | | | | |
| P12-T04 | 12 | Persistence failure handling | TODO | | | | | |
| P12-T05 | 12 | Cancellation | TODO | | | | | |
| P12-T06 | 12 | Performance metrics | TODO | | | | | |
| P13-T01 | 13 | Legacy-agent availability tests | TODO | | | | | |
| P13-T02 | 13 | UI mode tests | TODO | | | | | |
| P13-T03 | 13 | Tutor-loop regression tests | TODO | | | | | |
| P13-T04 | 13 | Chemistry-domain tests | TODO | | | | | |
| P13-T05 | 13 | RAG tests | TODO | | | | | |
| P13-T06 | 13 | General Assistant tests | TODO | | | | | |
| P13-T07 | 13 | Mode-boundary tests | TODO | | | | | |
| P13-T08 | 13 | Streaming tests | TODO | | | | | |
| P13-T09 | 13 | Cancellation tests | TODO | | | | | |
| P13-T10 | 13 | Persistence tests | TODO | | | | | |
| P13-T11 | 13 | Long-conversation tests | TODO | | | | | |
| P13-T12 | 13 | Release-readiness audit | TODO | | | | | |

---

# 31. SESSION HANDOFF TEMPLATE

At the end of every AI-agent session, update the tracker and append a short note:

```yaml
session_handoff:
  date: ""
  agent: ""
  completed_tasks:
    - ""
  current_task: ""
  verified_tests:
    - ""
  benchmark_results:
    - ""
  files_changed:
    - ""
  commit: ""
  known_failures:
    - ""
  blockers:
    - ""
  next_action: ""
  notes: ""
```

The next session MUST verify the handoff rather than trust it.

---

# 32. SOURCE REFERENCE

Primary repository:

https://github.com/ainabhinavsharma/Gayatri-Tutor-V3

Current README:

https://github.com/ainabhinavsharma/Gayatri-Tutor-V3/blob/main/README.md

Existing performance execution plan:

https://github.com/ainabhinavsharma/Gayatri-Tutor-V3/blob/main/Gayatri_Tutor_V4_Performance_Refactor_EXECUTION_PLAN.md

Existing performance summary:

https://github.com/ainabhinavsharma/Gayatri-Tutor-V3/blob/main/PERFORMANCE_REFACTOR_V4.md

Qwen2.5 model family reference:

https://huggingface.co/collections/Qwen/qwen25

---

# FINAL INSTRUCTION TO THE LOCAL AI AGENT

Start with **P0-T01**.

Do not modify Chemistry behavior, training data, UI architecture, or legacy-agent code until the actual repository state has been mapped and the tracker has been initialized.

Every change must answer:

```text
What changed?
Why was it needed?
Where did it change?
How was it verified?
What tests prove it?
What remains?
What is the next task?
```

The objective is not to preserve the current multi-agent design.

The objective is to turn Gayatri Tutor V3 into a focused, maintainable, local-first product whose active runtime has only:

```text
🧪 Chemistry Tutor
💬 General Assistant
```

with Chemistry Tutor behaving as an adaptive teacher rather than a generic chatbot, and with the architecture ready for future multi-user deployment without forcing a rewrite later.
