# Gayatri Tutor Chemistry --- AI Agent Engineering Execution Plan

**Repository:**
https://github.com/ainabhinavsharma/Gayatri-Tutor-Chemistry\
**Purpose:** Give a local AI coding agent a deterministic, resumable,
phase-by-phase implementation plan to audit, repair, test, and harden
the repository.

------------------------------------------------------------------------

# 0. NON-NEGOTIABLE AGENT RULES

The agent MUST follow these rules throughout the project.

1.  **Inspect before editing.**

    -   Read the relevant source files, tests, schemas, configuration
        and documentation.
    -   Never assume that a TODO or README statement represents actual
        implementation.

2.  **Verify every finding against the current checkout.**

    -   This document contains known findings.
    -   If code has changed since this document was created, re-check
        the finding before modifying it.

3.  **Never make the system look adaptive without making the underlying
    state adaptive.**

    -   Every adaptive decision must be explainable from persisted
        learner evidence.

4.  **Never use hard-coded learner state in production code.**

5.  **Never use keyword matching as the authoritative chemistry answer
    evaluator.**

6.  **Never silently turn an error into a successful learning event.**

7.  **Never silently turn evaluation failure into `incorrect`.**

    -   Use `uncertain` and preserve the evidence.

8.  **Never allow one student's learning state to affect another
    student's state.**

9.  **Never let General Assistant activity mutate Chemistry learning
    state.**

10. **Never allow Chemistry activity to contaminate General Assistant
    history.**

11. **Do not delete existing functionality merely to make tests pass.**

-   Replace or refactor it only when the new behavior is explicitly
    required.

12. **Do not use mocks/fakes as production replacements for broken
    subsystems.**

-   Mocks are allowed in tests.

13. **Do not silently expand the Chemistry curriculum beyond the
    configured scope.**

-   Current core scope: Thermodynamics + Inorganic Chemistry.

14. **Keep changes small and reviewable.**

-   Prefer one logical change per commit.

15. **Run targeted tests after each meaningful change.**

16. **Run the complete test suite at the end of every phase.**

17. **Do not mark a task DONE without evidence.**

18. **Update this document's progress tracker after every agent
    session.**

19. **If a session stops unexpectedly, resume from the tracker rather
    than starting again.**

20. **Never overwrite the tracker with guesses.**

-   Record `BLOCKED`, `FAILED`, or `NEEDS_REVIEW` when appropriate.

------------------------------------------------------------------------

# 1. PRODUCT TARGET

The repository must become a reliable Chemistry Tutor with a separate
General Assistant.

## Chemistry Tutor

Primary scope:

-   Thermodynamics
-   Inorganic Chemistry

Capabilities:

-   NCERT-aware tutoring
-   Concept-aware RAG
-   Guided explanation
-   Practice
-   Assessment
-   Adaptive difficulty
-   Mastery tracking
-   Misconception tracking
-   Spaced review
-   Prerequisite-aware sequencing
-   Progress reporting

## General Assistant

Capabilities may remain broad, but:

-   it must have separate conversation state;
-   it must not modify Chemistry mastery;
-   it must not appear in Chemistry progress;
-   it must not affect Chemistry adaptive decisions.

------------------------------------------------------------------------

# 2. DEFINITION OF DONE

The project is NOT production-ready until all of the following are true.

``` text
[ ] Student mastery is isolated per student.
[ ] Curriculum concepts are globally defined and learner state is separate.
[ ] Every learning event has a unique ID.
[ ] Every tutor turn has a unique turn ID.
[ ] Learning updates are idempotent.
[ ] Chemistry topic/concept is dynamically resolved.
[ ] No production runtime hard-codes Thermodynamics as the active topic.
[ ] Keyword-only answer evaluation is removed.
[ ] Evaluator understands question context.
[ ] Evaluator can return uncertain.
[ ] Numeric questions support tolerance/units.
[ ] Formula/reaction questions have structured evaluation.
[ ] Difficulty is evidence-driven.
[ ] Misconceptions are persisted.
[ ] Review scheduling is persisted.
[ ] Prerequisites use stable concept IDs.
[ ] Curriculum validation catches missing/cyclic prerequisites.
[ ] Assessment results update learner state.
[ ] Progress UI reads persisted state.
[ ] RAG is concept-aware.
[ ] NCERT evidence is distinguishable from fallback evidence.
[ ] RAG failure is observable.
[ ] General Assistant and Chemistry state are isolated.
[ ] Streaming evaluation cannot race with authoritative commits.
[ ] Interrupted turns can be recovered.
[ ] Database migrations are reproducible.
[ ] Full regression suite passes.
[ ] Documentation reflects actual runtime behavior.
[ ] Model configuration is internally consistent.
```

------------------------------------------------------------------------

# 3. KNOWN HIGH-PRIORITY DEFECTS

These are the initial P0/P1 issues to verify and fix.

## P0-01 --- Adaptive state is not connected end-to-end

### Problem

The runtime currently allows current-message evaluator confidence to
influence adaptation instead of treating persisted student/concept
evidence as authoritative.

### Required result

``` text
Student message
    ↓
Session state
    ↓
Active concept
    ↓
Persisted mastery
    ↓
Recent evidence
    ↓
Answer evaluation
    ↓
Learning-event creation
    ↓
Mastery update
    ↓
Misconception update
    ↓
Difficulty decision
    ↓
Next learning action
```

### Acceptance test

Given two students:

``` text
Student A: Hess's Law mastery = 0.85
Student B: Hess's Law mastery = 0.35
```

the same question/request must not result in identical adaptive
decisions solely because the current message is similar.

------------------------------------------------------------------------

# P0-02 --- Unsafe answer evaluator

### Problem

The current evaluator uses simplistic keyword/number heuristics.

Examples that must NOT independently establish correctness:

``` text
yes
correct
true
400
200
50
0
```

### Required replacement

Evaluator input:

``` json
{
  "question_id": "thermo.hess.001",
  "concept_id": "thermo.hess_law",
  "question": "...",
  "expected_answer": "...",
  "rubric": "...",
  "student_answer": "...",
  "question_type": "mcq|numeric|short_answer|reaction|explanation"
}
```

Evaluator output:

``` json
{
  "correctness": "correct|partially_correct|incorrect|uncertain",
  "confidence": 0.0,
  "concept_understanding": "sound|shaky|misconception|unknown",
  "error_type": "none|conceptual|arithmetic|formula|unit|reaction|notation|other",
  "misconception": null,
  "recommended_action": "advance|reinforce|remediate|prerequisite_review",
  "difficulty_delta": 0,
  "evidence": []
}
```

### Acceptance criteria

-   MCQ → deterministic answer-key comparison.
-   Numeric → tolerance + unit validation.
-   Formula → normalized/symbolic comparison where feasible.
-   Reaction → reactants/products/reagents/stoichiometry checks where
    supported.
-   Short answer → rubric-based evaluation.
-   Explanation → concept-rubric evaluation.
-   Ambiguous → `uncertain`.
-   `uncertain` must NOT change mastery.

------------------------------------------------------------------------

# P0-03 --- Thermodynamics hard-coded in Chemistry runtime

### Problem

Active learning context is hard-coded in runtime/memory/prompt
construction.

### Required

Resolve:

``` text
domain
chapter
topic
subtopic
concept_id
```

from:

1.  explicit active concept;
2.  current session state;
3.  user request;
4.  classifier;
5.  curriculum resolver.

Never use a hard-coded Thermodynamics value as a fallback for an unknown
topic.

### Acceptance test

Ask:

``` text
Explain ionization enthalpy.
```

The runtime must enter the relevant Inorganic Chemistry concept, not
Thermodynamics.

------------------------------------------------------------------------

# P0-04 --- Memory is not authoritative learner memory

### Problem

Tutor memory currently behaves primarily as a formatted prompt
structure.

### Required

Create a persisted learner state.

Minimum fields:

``` text
student_id
active_domain
active_chapter
active_topic
active_concept_id
mastery
confidence
difficulty
attempt_count
correct_count
hint_count
streak
recent_errors
misconceptions
last_practiced
next_review_at
learning_status
```

------------------------------------------------------------------------

# P0-05 --- Streaming/evaluator race

### Problem

Background/daemon evaluation can finish after response generation or
transaction completion.

### Required

Authoritative learning updates must be deterministic.

Preferred:

``` text
evaluate
→ generate
→ commit learning event
→ update learner state
→ commit turn
```

If asynchronous evaluation is required:

``` text
TURN
  ↓
PENDING_EVALUATION
  ↓
EVALUATION_COMPLETED
  ↓
IDEMPOTENT LEARNING UPDATE
```

No uncontrolled background thread may mutate authoritative state.

------------------------------------------------------------------------

# P0-06 --- Mastery model is too simplistic

Current scalar mastery/decay logic is insufficient as the complete
source of truth.

### Required

Use append-only learning evidence:

``` text
learning_event_id
student_id
session_id
turn_id
concept_id
question_id
timestamp
difficulty
question_type
correctness
confidence
hint_used
response_time
misconception_code
source
```

Mastery becomes a derived state backed by evidence.

------------------------------------------------------------------------

# P0-07 --- Prerequisite failures can be silently hidden

Distinguish:

``` text
MISSING_PREREQUISITE
```

from:

``` text
PREREQUISITE_NOT_MASTERED
```

Missing curriculum references must fail validation.

------------------------------------------------------------------------

# P0-08 --- Prerequisites need stable IDs

Replace free-text prerequisite references with stable IDs.

Example:

``` json
{
  "id": "inorganic.periodicity",
  "prerequisites": [
    "chem.atomic_structure",
    "chem.electronic_configuration"
  ]
}
```

------------------------------------------------------------------------

# P0-09 --- Mastery must be student-scoped

Global curriculum:

``` text
concepts
```

Learner-specific:

``` text
student_concept_mastery
```

Suggested schema:

``` sql
student_concept_mastery(
    student_id,
    concept_id,
    mastery,
    confidence,
    exposure_count,
    correct_count,
    error_count,
    last_practiced,
    next_review_at,
    difficulty_level,
    PRIMARY KEY(student_id, concept_id)
)
```

------------------------------------------------------------------------

# P0-10 --- Chemistry/General Assistant state isolation

Required invariants:

``` text
General message
→ Chemistry mastery unchanged

Chemistry answer
→ General history unchanged

Switch mode
→ Chemistry state retained

New Chemistry session
→ student mastery retained

Clear session
→ student-wide mastery retained unless explicit reset requested
```

------------------------------------------------------------------------

# 4. PHASE-BY-PHASE EXECUTION

# PHASE 0 --- BASELINE AND REPOSITORY DISCOVERY

## Objective

Establish exactly what currently works before changing anything.

## Tasks

### P0-T01 --- Capture environment

Record:

``` text
Python version
OS
Git commit
branch
dependency versions
model configuration
database path
environment variables required
```

### P0-T02 --- Run tests

Run all available:

``` bash
pytest
```

Also inspect:

``` bash
python -m compileall .
```

and project-specific lint/type checks if configured.

### P0-T03 --- Map architecture

Document:

``` text
entrypoints
runtime
orchestrator
tutor state machine
curriculum
LDG
database
RAG
evaluator
student adapter
memory
UI/API
tests
```

### P0-T04 --- Verify known findings

Do not blindly accept this document.

For each P0 finding:

``` text
CONFIRMED
NOT_REPRODUCED
ALREADY_FIXED
PARTIALLY_FIXED
```

### Exit criteria

``` text
[ ] Baseline tests recorded
[ ] Architecture map created
[ ] Every P0 finding verified
[ ] No code changed except optional instrumentation/documentation
```

------------------------------------------------------------------------

# PHASE 1 --- DATA MODEL AND STUDENT-SCOPED LEARNING STATE

## Objective

Make learner state trustworthy before implementing adaptation.

## Tasks

### P1-T01 --- Separate curriculum from learner state

Create global concept tables/models.

Create student-specific mastery tables/models.

### P1-T02 --- Add migrations

Migration system must support:

``` text
up
down/rollback where feasible
version detection
```

### P1-T03 --- Add learning events

Create append-only evidence records.

### P1-T04 --- Add turn IDs

Every tutor interaction gets:

``` text
student_id
session_id
turn_id
timestamp
```

### P1-T05 --- Add idempotency

The same learning event must not be applied twice.

### Tests

``` text
test_student_mastery_isolated
test_learning_event_unique
test_duplicate_event_is_idempotent
test_session_does_not_reset_mastery
test_general_mode_does_not_change_chemistry_mastery
```

### Exit criteria

``` text
[ ] Student-scoped mastery works
[ ] Learning events persist
[ ] Turn IDs exist
[ ] Duplicate updates are safe
[ ] Tests pass
```

------------------------------------------------------------------------

# PHASE 2 --- REBUILD THE CHEMISTRY ANSWER EVALUATOR

## Objective

Make evaluation chemically meaningful.

## Tasks

### P2-T01 --- Remove keyword correctness

Delete/disable production logic where words/numbers alone determine
correctness.

### P2-T02 --- Introduce structured evaluation contract

Implement the input/output contract defined in P0-02.

### P2-T03 --- Implement deterministic evaluators

At minimum:

``` text
MCQ
numeric
short_answer
formula
reaction
```

### P2-T04 --- Add uncertain state

An evaluator failure or ambiguous answer must return:

``` text
uncertain
```

not:

``` text
incorrect
```

### P2-T05 --- Add evidence

Every evaluation must explain which evidence produced the result.

### Tests

At minimum:

``` text
"yes" cannot prove a random question correct
"400" cannot prove a random question correct
correct numeric answer within tolerance → correct
numeric answer outside tolerance → incorrect
wrong unit → unit error
ambiguous answer → uncertain
uncertain → mastery unchanged
```

### Exit criteria

``` text
[ ] Keyword evaluator removed
[ ] Structured evaluator implemented
[ ] Uncertain state works
[ ] Tests cover false-positive regressions
```

------------------------------------------------------------------------

# PHASE 3 --- CONCEPT AND TOPIC RESOLUTION

## Objective

Make the active learning concept dynamic.

## Tasks

### P3-T01 --- Curriculum resolver

Implement:

``` text
resolve_domain()
resolve_chapter()
resolve_topic()
resolve_subtopic()
resolve_concept()
```

### P3-T02 --- Active concept state

Persist the active concept in session state.

### P3-T03 --- Context-aware classification

Classification must use:

``` text
current message
active concept
recent conversation
curriculum
```

### P3-T04 --- Remove hard-coded topic defaults

Search entire repository for:

``` text
Thermodynamics
General
hard-coded concept IDs
```

inside runtime state construction.

Replace inappropriate defaults with explicit `unknown`/resolver logic.

### Tests

``` text
ionization enthalpy → Inorganic Chemistry
Hess's law → Thermodynamics
Gibbs free energy → Thermodynamics
active concept persists across turns
new explicit topic overrides old active topic
```

### Exit criteria

``` text
[ ] No inappropriate hard-coded active topic
[ ] Concept resolver works
[ ] Active concept persists
[ ] Tests pass
```

------------------------------------------------------------------------

# PHASE 4 --- ADAPTIVE LEARNING ENGINE

## Objective

Turn learner evidence into deterministic adaptive decisions.

Create or consolidate:

``` text
core/learning/
    state.py
    events.py
    mastery.py
    scheduler.py
    selector.py
    misconceptions.py
    progress.py
    policy.py
```

## P4-T01 --- Mastery engine

Maintain:

``` text
mastery
confidence
evidence_count
independent_success
recent_accuracy
long_term_accuracy
```

Start with a transparent configurable model.

Example:

``` text
mastery =
    0.45 * recent_accuracy
  + 0.25 * long_term_accuracy
  + 0.15 * difficulty_adjusted_score
  + 0.10 * independent_success
  + 0.05 * retention_score
```

Clamp:

``` text
0.0 <= mastery <= 1.0
```

Do not hard-code the weights in multiple places.

## P4-T02 --- Difficulty policy

Levels:

``` text
1 Recall
2 Basic application
3 Standard application
4 Multi-step
5 Advanced/exam-style
```

Rules:

``` text
2+ independent correct → +1 difficulty
correct with hint → maintain
partial → maintain/reduce
conceptual error → reduce
two consecutive conceptual errors → prerequisite review
```

## P4-T03 --- Misconception tracking

Use controlled misconception codes.

### Thermodynamics

``` text
THERMO_SIGN_CONVENTION
HEAT_VS_INTERNAL_ENERGY
STATE_VS_PATH_FUNCTION
ENTHALPY_CONFUSION
HESS_LAW_DIRECTION
CP_CV_CONFUSION
GIBBS_SIGN_CONFUSION
```

### Inorganic

``` text
PERIODIC_TREND_CONFUSION
OXIDATION_STATE_ERROR
ELECTRONIC_CONFIGURATION_ERROR
COORDINATION_NUMBER_CONFUSION
LIGAND_CONFUSION
REDOX_CONFUSION
ANOMALOUS_BEHAVIOUR_CONFUSION
METALLURGY_PROCESS_CONFUSION
```

## P4-T04 --- Concept selector

Rank candidate concepts using:

``` text
prerequisite readiness
× mastery gap
× review urgency
× curriculum importance
× misconception risk
```

## Exit criteria

A test must be able to demonstrate:

``` text
weak student → easier/remedial question
strong student → harder question
repeated error → misconception path
mastered + due review → review question
```

------------------------------------------------------------------------

# PHASE 5 --- SPACED REVIEW

## Objective

Ensure learning is retained, not merely completed.

## P5-T01 --- Add review schedule

Store:

``` text
next_review_at
interval
review_count
last_review_result
```

## P5-T02 --- Initial intervals

Use configurable defaults:

``` text
1 day
3 days
7 days
14 days
30 days
```

## P5-T03 --- Adapt intervals

Success:

``` text
increase interval
```

Failure:

``` text
shorten interval
```

Hints/partial:

``` text
smaller increase or no increase
```

## P5-T04 --- Retention requirement

A concept cannot be marked fully mastered solely from immediate success.

Require delayed recall evidence.

## Exit criteria

``` text
[ ] Due reviews are detected
[ ] Reviews affect mastery
[ ] Review intervals adapt
[ ] Mastery requires retention evidence
```

------------------------------------------------------------------------

# PHASE 6 --- ASSESSMENT ENGINE

## Objective

Separate tutoring from controlled measurement.

## P6-T01 --- Question bank schema

Each question:

``` json
{
  "id": "thermo.hess.001",
  "concept_id": "thermo.hess_law",
  "difficulty": 3,
  "type": "numeric",
  "question": "...",
  "answer": "...",
  "rubric": "...",
  "hint": "...",
  "explanation": "...",
  "common_misconceptions": [],
  "source": "NCERT"
}
```

## P6-T02 --- Assessment session

Persist:

``` text
assessment_id
student_id
concepts
question_ids
start_time
end_time
status
score
```

## P6-T03 --- Attempt records

Persist every attempt.

## P6-T04 --- Assessment result

Return:

``` text
score
concept strengths
concept weaknesses
misconceptions
recommended remediation
next review
```

## Exit criteria

``` text
[ ] Assessment can be resumed
[ ] Every answer maps to a question
[ ] Score is reproducible
[ ] Assessment changes learning state correctly
```

------------------------------------------------------------------------

# PHASE 7 --- NCERT RAG AND EVIDENCE CONTROL

## Objective

Make retrieval useful for tutoring without allowing evidence drift.

## P7-T01 --- Concept-aware retrieval

Query must combine:

``` text
user question
active domain
chapter
topic
concept
learning objective
```

## P7-T02 --- Source provenance

Every retrieved chunk should identify:

``` text
source
chapter
page/section if available
retrieval score
```

## P7-T03 --- Source priority

Preferred order:

``` text
NCERT
configured trusted curriculum material
controlled fallback
```

## P7-T04 --- RAG failure handling

Never silently switch to unrestricted generation.

Record:

``` text
RAG_STATUS_OK
RAG_STATUS_EMPTY
RAG_STATUS_ERROR
```

## Exit criteria

``` text
[ ] Retrieval is concept-aware
[ ] Source is visible to runtime
[ ] RAG failures are observable
[ ] Retrieval tests pass
```

------------------------------------------------------------------------

# PHASE 8 --- TUTOR STATE MACHINE INTEGRATION

## Objective

Make the state machine authoritative rather than decorative.

Required flow:

``` text
DISCOVERING
    ↓
EXPLAINING
    ↓
EXAMPLE
    ↓
CHECKING
    ↓
EVALUATING
    ↓
+-------------------+
|                   |
v                   v
REMEDIATING      PRACTICING
|                   |
+--------→ CHECKING
             ↓
        COMPLETED
```

## Rules

-   Assessment suppresses unnecessary hints.
-   Remediation uses misconception evidence.
-   Practice uses adaptive difficulty.
-   Completion requires mastery criteria.
-   State transitions are persisted where recovery requires them.

------------------------------------------------------------------------

# PHASE 9 --- PROGRESS AND ANALYTICS

## Objective

Make progress visible and derived from persisted evidence.

## Dashboard

### Overall

``` text
Overall mastery
Thermodynamics mastery
Inorganic Chemistry mastery
```

### Topic

``` text
Topic mastery
Questions attempted
Accuracy
Difficulty
Misconceptions
Review due
```

### Status

``` text
NEW
LEARNING
PRACTICING
PROFICIENT
MASTERED
REVIEW_DUE
```

## Important rule

Never calculate progress independently in multiple UI components.

Create one progress service/API.

``` text
persisted events
      ↓
learning engine
      ↓
progress service
      ↓
UI
```

------------------------------------------------------------------------

# PHASE 10 --- RELIABILITY, CONCURRENCY AND RECOVERY

## Objective

Prevent silent data corruption.

## P10-T01 --- Turn lifecycle

Persist:

``` text
TURN_STARTED
EVALUATION_STARTED
RESPONSE_GENERATED
EVALUATION_COMPLETED
LEARNING_STATE_UPDATED
TURN_COMMITTED
```

Failure:

``` text
TURN_ABORTED
```

## P10-T02 --- Recovery

On startup:

``` text
find incomplete turns
→ classify recoverable/unrecoverable
→ retry safe operations
→ never duplicate learning events
```

## P10-T03 --- Remove uncontrolled daemon mutation

No background task may update authoritative learner state without:

``` text
turn_id
event_id
idempotency
error handling
persistence verification
```

------------------------------------------------------------------------

# PHASE 11 --- CURRICULUM VALIDATION

## Objective

Make the curriculum structurally trustworthy.

Validation must detect:

``` text
duplicate concept IDs
missing prerequisite IDs
cycles
orphan concepts
invalid domains
invalid difficulty
missing learning outcomes
missing question mappings
```

CI must fail when curriculum validation fails.

------------------------------------------------------------------------

# PHASE 12 --- SECURITY AND DATA ISOLATION

## Objective

Prevent learner data leakage.

Check:

``` text
student ID authorization
session ownership
database queries
API endpoints
logs
error messages
prompt construction
RAG filters
cached state
```

Never log:

``` text
passwords
tokens
private credentials
full sensitive student records
```

Test:

``` text
Student A cannot request Student B's progress by changing an ID.
```

------------------------------------------------------------------------

# PHASE 13 --- MODEL AND CONFIGURATION CONSISTENCY

## Objective

Make model deployment reproducible.

Create a single model manifest:

``` json
{
  "model_name": "...",
  "base_model": "...",
  "adapter": "...",
  "quantization": "...",
  "context_length": 8192,
  "training_dataset_version": "...",
  "created_at": "...",
  "sha256": "..."
}
```

Ensure:

``` text
README model
=
config model
=
runtime model
=
training model
=
deployment model
```

No conflicting model names/checkpoints.

------------------------------------------------------------------------

# PHASE 14 --- DOCUMENTATION AND CLEANUP

Update:

``` text
README.md
CONTRIBUTING.md
CHANGELOG.md
docs/
```

README must explain:

-   product purpose;
-   Chemistry scope;
-   General Assistant;
-   architecture;
-   adaptive learning;
-   mastery;
-   assessment;
-   RAG;
-   installation;
-   environment variables;
-   model configuration;
-   database migrations;
-   tests;
-   limitations;
-   contribution workflow.

Remove obsolete generic-agent descriptions where they no longer reflect
runtime behavior.

------------------------------------------------------------------------

# 5. TEST MATRIX

The agent must build a regression suite around the following.

## Evaluator

``` text
[ ] correct MCQ
[ ] wrong MCQ
[ ] correct numeric within tolerance
[ ] incorrect numeric
[ ] unit mismatch
[ ] correct formula
[ ] incorrect formula
[ ] correct reaction
[ ] incorrect reaction
[ ] partial explanation
[ ] conceptual misconception
[ ] ambiguous answer
[ ] evaluator failure
```

## Mastery

``` text
[ ] correct increases evidence
[ ] incorrect produces negative evidence
[ ] uncertain does not alter mastery
[ ] hints affect evidence
[ ] mastery bounded
[ ] student isolation
```

## Difficulty

``` text
[ ] strong performance increases difficulty
[ ] hint-supported success maintains difficulty
[ ] partial answer maintains/reduces difficulty
[ ] conceptual errors reduce difficulty
[ ] repeated errors trigger prerequisite review
```

## Scheduling

``` text
[ ] new concept
[ ] successful review
[ ] failed review
[ ] due review
[ ] overdue review
```

## Curriculum

``` text
[ ] valid concept IDs
[ ] valid prerequisite IDs
[ ] no cycles
[ ] no orphan prerequisites
[ ] valid difficulty
```

## Mode isolation

``` text
[ ] General → Chemistry unchanged
[ ] Chemistry → General unchanged
[ ] switching modes preserves each state
```

## Security

``` text
[ ] cross-user progress access blocked
[ ] session ownership enforced
[ ] sensitive data absent from logs
```

------------------------------------------------------------------------

# 6. ADAPTIVE LEARNING ACCEPTANCE SCENARIOS

These scenarios are mandatory.

## Scenario A --- Beginner

``` text
Student mastery:
Hess's Law = 0.20

Student answers incorrectly twice.

Expected:
- misconception detected
- difficulty decreases
- remediation selected
- prerequisite check performed
- review scheduled sooner
```

## Scenario B --- Strong learner

``` text
Student mastery:
Hess's Law = 0.88

Student answers two independent questions correctly.

Expected:
- difficulty increases
- no unnecessary remediation
- concept may become eligible for delayed review
```

## Scenario C --- Hint dependency

``` text
Student repeatedly answers correctly only after hints.

Expected:
- mastery grows more slowly
- difficulty does not immediately increase
- independent recall is scheduled
```

## Scenario D --- Retention failure

``` text
Student previously mastered concept.
Delayed review fails.

Expected:
- mastery/evidence reflects the failure
- review interval shortens
- concept returns to practice
```

## Scenario E --- Inorganic vs Thermodynamics isolation

``` text
Student has:
Thermodynamics mastery = 0.80

No Inorganic evidence.

Student asks about ionization enthalpy.

Expected:
- active domain = Inorganic Chemistry
- no Thermodynamics mastery mutation
- Inorganic state created/updated independently
```

## Scenario F --- Two students

``` text
Student A:
Hess's Law = 0.90

Student B:
Hess's Law = 0.20
```

Expected:

``` text
A receives advanced practice.
B receives foundational/remedial practice.
```

The decision must be derived from persisted student-specific evidence.

------------------------------------------------------------------------

# 7. AGENT SESSION PROTOCOL

At the beginning of EVERY coding session:

``` text
1. Read this document.
2. Read PROGRESS_TRACKER.yaml.
3. Inspect git status.
4. Inspect current branch.
5. Read the last completed task.
6. Read changed files from the last session.
7. Run the smallest relevant test set.
8. Continue from the next unfinished task.
```

At the end of EVERY coding session:

``` text
1. Run targeted tests.
2. Run relevant integration tests.
3. Update tracker.
4. Record failures.
5. Record blockers.
6. Record changed files.
7. Record next exact task.
8. Record commit hash if committed.
```

------------------------------------------------------------------------

# 8. PROGRESS TRACKER

Create this file at repository root:

``` text
PROGRESS_TRACKER.yaml
```

Use:

``` yaml
project: Gayatri Tutor Chemistry
status: IN_PROGRESS

current_phase: 0
current_task: P0-T01

last_completed_task: null
last_verified_commit: null

baseline:
  python_version: null
  os: null
  git_commit: null
  test_command: null
  tests_passed: null
  tests_failed: null
  tests_skipped: null

phases:
  phase_0_baseline: TODO
  phase_1_learning_state: TODO
  phase_2_evaluator: TODO
  phase_3_concept_resolution: TODO
  phase_4_adaptive_engine: TODO
  phase_5_spaced_review: TODO
  phase_6_assessment: TODO
  phase_7_rag: TODO
  phase_8_state_machine: TODO
  phase_9_progress: TODO
  phase_10_reliability: TODO
  phase_11_curriculum_validation: TODO
  phase_12_security: TODO
  phase_13_model_config: TODO
  phase_14_documentation: TODO

critical_bugs:
  P0-01: TODO
  P0-02: TODO
  P0-03: TODO
  P0-04: TODO
  P0-05: TODO
  P0-06: TODO
  P0-07: TODO
  P0-08: TODO
  P0-09: TODO
  P0-10: TODO

adaptive_learning:
  student_scoped_mastery: TODO
  learning_events: TODO
  evaluator: TODO
  topic_resolution: TODO
  mastery_engine: TODO
  difficulty_engine: TODO
  misconception_tracking: TODO
  spaced_review: TODO
  assessment_engine: TODO
  progress_service: TODO
  rag_integration: TODO

tests:
  unit: TODO
  integration: TODO
  regression: TODO
  security: TODO
  curriculum_validation: TODO

last_session:
  date: null
  summary: null
  files_changed: []
  tests_run: []
  tests_passed: []
  tests_failed: []
  blockers: []

next_action: >
  Inspect the repository and complete the next unfinished task.
```

------------------------------------------------------------------------

# 9. TASK STATUS RULES

Allowed task states:

``` text
TODO
IN_PROGRESS
BLOCKED
FAILED
NEEDS_REVIEW
DONE
```

A task can be `DONE` only if:

``` text
implementation exists
AND
tests exist where appropriate
AND
tests pass
AND
behavior was manually verified where necessary
AND
tracker is updated
```

A phase can be `DONE` only when all tasks in that phase are DONE.

------------------------------------------------------------------------

# 10. COMMIT STRATEGY

Recommended commits:

``` text
chore: establish chemistry tutor baseline
fix: isolate student learning state
fix: replace keyword answer evaluator
fix: resolve active chemistry concept
feat: add evidence based mastery engine
feat: add adaptive difficulty policy
feat: add misconception tracking
feat: add spaced review scheduler
feat: add assessment engine
fix: integrate concept aware chemistry rag
fix: remove streaming learning race
feat: add progress service
test: add adaptive learning regression suite
fix: harden student data isolation
docs: update chemistry tutor architecture
```

Never create one giant commit containing all phases.

------------------------------------------------------------------------

# 11. WHAT NOT TO DO

Do NOT:

``` text
- train a larger model to compensate for broken state management
- add more prompts instead of fixing evaluator logic
- add UI progress based on temporary in-memory variables
- make every answer "adaptive" through an LLM prompt
- use LLM confidence as the only mastery signal
- silently default unknown concepts to Thermodynamics
- silently mark evaluation failures as incorrect
- store mastery globally
- use free-text prerequisite names as graph identifiers
- bypass prerequisite validation
- hide exceptions behind broad except blocks
- start uncontrolled daemon threads for learning-state mutation
- delete tests because they expose architecture problems
- mark TODOs as completed without evidence
```

------------------------------------------------------------------------

# 12. FINAL ARCHITECTURAL INVARIANT

The final system must always be able to answer:

``` text
Why did the tutor choose this concept?
Why did it choose this difficulty?
What does it believe the student knows?
What evidence produced that belief?
What misconception was detected?
When should the student review the concept?
What will happen after the student's next answer?
```

The answer to each question must come from **persisted, inspectable
learning state and deterministic policy**, not from an unexplained LLM
response.

The fundamental loop is:

``` text
             ┌─────────────────────────┐
             │                         │
             v                         │
       Student Evidence               │
             │                         │
             v                         │
      Answer Evaluation               │
             │                         │
             v                         │
       Learning Event                 │
             │                         │
             v                         │
      Student Mastery State           │
             │                         │
             v                         │
   Adaptive Policy / Scheduler        │
             │                         │
             v                         │
       Next Learning Action           │
             │                         │
             v                         │
        Tutor Response                │
             │                         │
             └─────────────────────────┘
```

If this loop is correct, the model can be replaced or upgraded without
destroying the learner's progress.

If this loop is not correct, the application is not yet a reliable
adaptive tutor.
