# Gayatri Tutor Chemistry --- Current-State Re-Audit & Local AI Agent Fix Plan

**Repository:**
https://github.com/ainabhinavsharma/Gayatri-Tutor-Chemistry\
**Plan generated:** 2026-09-19\
**Purpose:** Give a local AI coding agent a resumable, evidence-driven
plan to determine what has been fixed since the previous audit, identify
regressions/new bugs, and finish the Chemistry Tutor.

------------------------------------------------------------------------

# 0. IMPORTANT --- CURRENT RE-AUDIT STATUS

The previous audit identified major issues around:

-   student-scoped mastery;
-   answer evaluation;
-   hard-coded Thermodynamics state;
-   streaming/evaluation race conditions;
-   adaptive learning;
-   prerequisite handling;
-   RAG;
-   progress tracking;
-   Chemistry/General Assistant isolation.

For this re-audit, the public GitHub repository could not be fetched
reliably from the current web/container environment. Therefore this
document **must not be treated as proof that any previous issue is still
present or already fixed**.

The local AI agent MUST perform a fresh checkout and verify every item
against the actual current HEAD.

The agent must classify every previous finding as exactly one of:

``` text
FIXED
PARTIALLY_FIXED
NOT_FIXED
REGRESSED
NOT_REPRODUCED
BLOCKED
```

Do not infer status from commit messages, filenames, TODOs, README
claims, or previous tracker values alone.

------------------------------------------------------------------------

# 1. PRIMARY OBJECTIVE

Turn the repository into a reliable adaptive Chemistry Tutor.

The target learning loop is:

``` text
Student interaction
       ↓
Session + active concept
       ↓
Student-specific learning state
       ↓
Question/answer evaluation
       ↓
Learning event
       ↓
Mastery + misconception update
       ↓
Adaptive policy
       ↓
Next concept / difficulty / action
       ↓
Tutor response
       ↓
New evidence
```

Every decision must be explainable from persisted evidence.

If the system cannot answer:

``` text
Why this concept?
Why this difficulty?
What does the student know?
What evidence changed mastery?
What misconception was detected?
When should this be reviewed?
```

then adaptive learning is not complete.

------------------------------------------------------------------------

# 2. AGENT OPERATING RULES

The local agent MUST:

1.  Work from the actual checked-out repository.
2.  Start by reading this file and `PROGRESS_TRACKER.yaml`.
3.  Inspect `git status`, current branch, HEAD and recent commits.
4.  Run baseline tests before modifying code.
5.  Verify previous fixes rather than assuming them.
6.  Never mark a task DONE without test evidence.
7.  Never replace broken production logic with mocks.
8.  Never delete tests just because they fail.
9.  Never hide exceptions affecting learning correctness.
10. Never use an LLM's free-form confidence as the sole mastery signal.
11. Never use keyword matching as authoritative chemistry evaluation.
12. Never silently default unknown concepts to Thermodynamics.
13. Never allow cross-student learning-state leakage.
14. Never let General Assistant state modify Chemistry state.
15. Make small commits.
16. Update `PROGRESS_TRACKER.yaml` after every meaningful session.
17. If work is interrupted, resume from the tracker.
18. Run targeted tests after each logical fix.
19. Run the full suite at the end of each phase.
20. Record blockers instead of inventing completion.

------------------------------------------------------------------------

# 3. PHASE 0 --- FRESH REPOSITORY RE-AUDIT

## Goal

Determine exactly what changed since the previous audit.

## 0.1 Repository snapshot

Run:

``` bash
git status --short
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -20
git diff
git tag --list
```

Record:

``` yaml
head_commit:
branch:
dirty_worktree:
recent_commits:
```

## 0.2 Environment snapshot

Record:

``` bash
python --version
pip freeze
```

Also identify:

``` text
database engine/version
LLM/model configuration
embedding model
vector store
runtime server
frontend framework
test framework
```

## 0.3 Test baseline

Run all configured tests.

Suggested:

``` bash
pytest -q
python -m compileall .
```

Also run configured lint/type checks.

Record:

``` text
passed
failed
skipped
errors
warnings
```

## 0.4 Repository architecture scan

Map:

``` text
entrypoints
core runtime
orchestrator
Chemistry runtime
General Assistant runtime
state machine
curriculum
LDG
database
student state
evaluator
adapter
memory
RAG
question bank
assessment
progress API/UI
configuration
tests
```

## 0.5 Previous finding verification

Create:

``` text
AUDIT_REVERIFICATION.md
```

with this table:

  Finding                  Status   Evidence   Tests   Remaining Work
  ------------------------ -------- ---------- ------- ----------------
  P0-01 Adaptive state     TODO                        
  P0-02 Evaluator          TODO                        
  P0-03 Hard-coded topic   TODO                        
  P0-04 Memory             TODO                        
  P0-05 Streaming race     TODO                        
  P0-06 Mastery model      TODO                        
  P0-07 Prerequisites      TODO                        
  P0-08 Stable IDs         TODO                        
  P0-09 Student scope      TODO                        
  P0-10 Mode isolation     TODO                        

Status MUST be one of:

``` text
FIXED
PARTIALLY_FIXED
NOT_FIXED
REGRESSED
NOT_REPRODUCED
BLOCKED
```

### Phase 0 exit criteria

``` text
[ ] Current HEAD recorded
[ ] Baseline test result recorded
[ ] Architecture mapped
[ ] Previous findings reverified
[ ] New bugs logged
[ ] AUDIT_REVERIFICATION.md created
[ ] PROGRESS_TRACKER.yaml updated
```

------------------------------------------------------------------------

# 4. BUG SEVERITY MODEL

Use:

## P0 --- Critical

Breaks learning correctness, data integrity, security or core runtime.

Examples:

``` text
cross-user mastery leakage
incorrect mastery mutation
lost learning events
race condition causing incorrect state
runtime cannot start
answer evaluator produces systematic false results
```

## P1 --- High

Major feature incorrect or unreliable.

Examples:

``` text
adaptive difficulty wrong
concept resolver unreliable
RAG silently fails
assessment does not update progress
review scheduling broken
```

## P2 --- Medium

Important UX/maintainability issue.

Examples:

``` text
progress display stale
poor recovery
weak validation
documentation mismatch
```

## P3 --- Low

Polish or non-critical improvement.

------------------------------------------------------------------------

# 5. PHASE 1 --- LEARNING STATE AUDIT AND REPAIR

## Goal

Make student state trustworthy.

## Check

Determine whether the current repository has:

``` text
student identity
student-scoped concept mastery
learning events
turn IDs
idempotency
misconceptions
review schedule
```

## Required model

Global:

``` text
concept
curriculum
prerequisite
question
```

Student-specific:

``` text
student_concept_mastery
learning_event
misconception
review_schedule
assessment_attempt
```

## Required minimum mastery fields

``` text
student_id
concept_id
mastery
confidence
exposure_count
correct_count
error_count
hint_count
last_practiced
next_review_at
difficulty_level
learning_status
```

## Required learning event

``` text
event_id
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

## Critical tests

``` text
test_student_a_cannot_modify_student_b
test_student_a_progress_not_visible_to_student_b
test_learning_event_idempotent
test_duplicate_event_not_applied_twice
test_session_reset_does_not_delete_mastery
```

### Exit

``` text
[ ] Student scope verified
[ ] Persistence verified
[ ] Idempotency verified
[ ] Migration verified
[ ] Tests pass
```

------------------------------------------------------------------------

# 6. PHASE 2 --- ANSWER EVALUATOR RE-AUDIT

## Goal

Ensure chemistry answers are evaluated against the question.

Search the entire repository for:

``` text
correct
incorrect
yes
true
false
keyword
contains(
regex
```

Identify any correctness logic based solely on text fragments.

## Required evaluator contract

``` json
{
  "question_id": "...",
  "concept_id": "...",
  "question": "...",
  "expected_answer": "...",
  "rubric": "...",
  "student_answer": "...",
  "question_type": "mcq|numeric|short_answer|reaction|formula|explanation"
}
```

Output:

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

## Required behavior

### MCQ

Use answer key.

### Numeric

Support:

``` text
absolute tolerance
relative tolerance
units
scientific notation
sign
```

### Formula

Normalize where practical.

### Reaction

Validate:

``` text
reactants
products
stoichiometry
reagents/conditions
```

### Explanation

Use rubric-based concept evaluation.

### Uncertain

If evaluation cannot confidently determine correctness:

``` text
correctness = uncertain
```

and:

``` text
mastery must not change
```

## Regression tests

These must all exist:

``` text
"yes" cannot prove arbitrary question correct
"correct" cannot prove arbitrary question correct
"400" cannot prove arbitrary question correct
"0" cannot prove arbitrary question correct
```

------------------------------------------------------------------------

# 7. PHASE 3 --- ACTIVE CONCEPT RESOLUTION

## Goal

Remove topic drift and hard-coded Thermodynamics behavior.

## Required resolution chain

``` text
explicit user request
      ↓
active concept
      ↓
recent context
      ↓
concept classifier
      ↓
curriculum graph
```

Resolve:

``` text
domain
chapter
topic
subtopic
concept_id
```

## Tests

``` text
"Hess's law" → Thermodynamics
"Gibbs free energy" → Thermodynamics
"ionization enthalpy" → Inorganic Chemistry
"electronic configuration" → Inorganic prerequisite
```

## Critical repository scan

Search for hard-coded:

``` text
Thermodynamics
General
concept_id
topic=
subtopic=
```

inside runtime state construction.

A hard-coded curriculum definition is acceptable.

A hard-coded active learner state is NOT.

------------------------------------------------------------------------

# 8. PHASE 4 --- ADAPTIVE MASTERy ENGINE

## Goal

Ensure adaptation is driven by evidence.

Create or verify:

``` text
core/learning/state.py
core/learning/events.py
core/learning/mastery.py
core/learning/policy.py
core/learning/selector.py
core/learning/misconceptions.py
core/learning/scheduler.py
```

## Mastery

The exact formula may differ, but it must incorporate multiple evidence
signals.

Possible baseline:

``` text
mastery =
    0.45 recent_accuracy
  + 0.25 long_term_accuracy
  + 0.15 difficulty_adjusted_score
  + 0.10 independent_success
  + 0.05 retention_score
```

Make weights configurable.

Never calculate mastery from one LLM response.

## Difficulty

Levels:

``` text
1 Recall
2 Basic application
3 Standard application
4 Multi-step
5 Advanced
```

Expected policy:

``` text
2+ independent correct → increase
correct with hint → maintain
partial → maintain/reduce
conceptual error → reduce
repeated conceptual error → prerequisite remediation
```

## Adaptive selection

Candidate score should consider:

``` text
prerequisite readiness
mastery gap
review urgency
curriculum importance
misconception risk
```

------------------------------------------------------------------------

# 9. PHASE 5 --- MISCONCEPTION ENGINE

## Goal

Track WHY the learner is wrong.

Minimum Thermodynamics codes:

``` text
THERMO_SIGN_CONVENTION
HEAT_VS_INTERNAL_ENERGY
STATE_VS_PATH_FUNCTION
ENTHALPY_CONFUSION
HESS_LAW_DIRECTION
CP_CV_CONFUSION
GIBBS_SIGN_CONFUSION
```

Minimum Inorganic codes:

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

## Required behavior

``` text
wrong answer
    ↓
identify error
    ↓
map misconception
    ↓
persist misconception
    ↓
select remediation
    ↓
test misconception again
```

Do not simply reduce difficulty without identifying the likely reason.

------------------------------------------------------------------------

# 10. PHASE 6 --- SPACED REVIEW

## Goal

Prevent false mastery.

Required fields:

``` text
next_review_at
interval
review_count
last_result
```

Initial configurable schedule:

``` text
1 day
3 days
7 days
14 days
30 days
```

Failure shortens interval.

Success extends interval.

Hint-dependent success should extend less than independent recall.

## Mastery rule

A concept must not be marked fully mastered solely from immediate
success.

Require delayed recall evidence.

------------------------------------------------------------------------

# 11. PHASE 7 --- ASSESSMENT ENGINE

## Required question schema

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

## Assessment must persist

``` text
assessment_id
student_id
question_ids
concept_ids
start_time
end_time
status
score
```

Every attempt must persist.

Assessment results must update learning events.

------------------------------------------------------------------------

# 12. PHASE 8 --- CURRICULUM / LDG VALIDATION

## Validate

``` text
unique concept IDs
valid prerequisite IDs
no cycles
no orphan concepts
valid domain
valid topic
valid difficulty
learning outcomes
question mappings
```

## Prerequisite representation

Prefer:

``` json
"prerequisites": [
  "chem.atomic_structure",
  "chem.electronic_configuration"
]
```

not:

``` json
"prerequisites": [
  "Atomic structure",
  "Electronic configuration"
]
```

CI should fail on curriculum errors.

------------------------------------------------------------------------

# 13. PHASE 9 --- RAG RE-AUDIT

## Goal

Prevent retrieval drift.

Retrieval input should include:

``` text
user question
domain
chapter
topic
concept
learning objective
```

## Source priority

``` text
NCERT
→ configured trusted curriculum
→ controlled fallback
```

Do not silently replace failed retrieval with unrestricted generation.

Track:

``` text
RAG_OK
RAG_EMPTY
RAG_ERROR
```

Every evidence chunk should retain provenance:

``` text
source
chapter
page/section
chunk ID
retrieval score
```

------------------------------------------------------------------------

# 14. PHASE 10 --- STREAMING / CONCURRENCY AUDIT

## Goal

Eliminate state corruption caused by asynchronous evaluation.

Search for:

``` text
Thread
daemon
async
create_task
background
stream
```

Identify every path capable of mutating:

``` text
mastery
learning events
misconceptions
review schedule
session state
```

## Required turn lifecycle

``` text
TURN_STARTED
    ↓
EVALUATION_STARTED
    ↓
RESPONSE_GENERATED
    ↓
EVALUATION_COMPLETED
    ↓
LEARNING_STATE_UPDATED
    ↓
TURN_COMMITTED
```

Failure:

``` text
TURN_ABORTED
```

Async evaluation is permitted only when it is:

``` text
identified by turn_id
idempotent
persisted
retryable
observable
```

------------------------------------------------------------------------

# 15. PHASE 11 --- GENERAL ASSISTANT / CHEMISTRY ISOLATION

Mandatory tests:

``` text
general message → Chemistry mastery unchanged
chemistry message → General history unchanged
switch mode → state preserved
new session → student mastery preserved
clear session → student mastery preserved
```

Inspect:

``` text
session stores
prompt memory
cache
database queries
API parameters
user IDs
mode identifiers
```

------------------------------------------------------------------------

# 16. PHASE 12 --- PROGRESS SYSTEM

Progress must be derived from the same persisted learning state used by
adaptation.

## Overall

``` text
Overall mastery
Thermodynamics mastery
Inorganic Chemistry mastery
```

## Topic

``` text
mastery
accuracy
attempts
difficulty
misconceptions
review due
```

## Status

``` text
NEW
LEARNING
PRACTICING
PROFICIENT
MASTERED
REVIEW_DUE
```

Do not calculate separate conflicting mastery values in the UI.

Architecture:

``` text
Learning events
      ↓
Learning engine
      ↓
Progress service
      ↓
API
      ↓
UI
```

------------------------------------------------------------------------

# 17. PHASE 13 --- SILENT FAILURE AUDIT

Search for:

``` python
except Exception:
    pass
```

and broad exception handling.

Review every:

``` text
return None
return {}
return []
fallback
default
try/except
```

Ask:

``` text
Does this hide a learning failure?
Does this hide a database failure?
Does this hide RAG failure?
Does this hide evaluator failure?
Does this hide model failure?
```

If yes, replace with explicit status/error handling.

## Forbidden conversions

``` text
evaluation failure → incorrect
missing curriculum → empty curriculum
RAG failure → unrestricted answer
database failure → success
missing student state → global state
```

------------------------------------------------------------------------

# 18. PHASE 14 --- DATABASE AND MIGRATION AUDIT

Verify:

``` text
schema version
migration order
rollback/recovery
foreign keys
indexes
unique constraints
transactions
```

Recommended indexes:

``` text
(student_id, concept_id)
(student_id, next_review_at)
(student_id, timestamp)
(concept_id, timestamp)
(turn_id)
(event_id)
```

Check transaction behavior under:

``` text
duplicate request
process crash
database timeout
partial write
retry
```

------------------------------------------------------------------------

# 19. PHASE 15 --- SECURITY / DATA LEAK AUDIT

Check:

``` text
authentication
authorization
student ID validation
session ownership
API access
logs
error responses
prompt context
RAG filters
cache keys
```

Mandatory test:

``` text
Student A must not be able to retrieve Student B's:
- mastery
- misconceptions
- assessment history
- conversations
- review schedule
```

Also verify secrets are not committed.

Search:

``` bash
git grep -n "API_KEY"
git grep -n "SECRET"
git grep -n "PASSWORD"
git grep -n "TOKEN"
```

Use environment variables/configuration for credentials.

------------------------------------------------------------------------

# 20. PHASE 16 --- MODEL CONFIGURATION AUDIT

There must be one authoritative model manifest.

Example:

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

Verify consistency between:

``` text
README
environment
config
runtime
training
deployment
```

No stale model references.

------------------------------------------------------------------------

# 21. PHASE 17 --- TEST HARDENING

Build tests for every fixed bug.

## Unit

``` text
curriculum
mastery
evaluator
difficulty
misconceptions
scheduler
RAG
state machine
```

## Integration

``` text
question → evaluation → event → mastery → adaptive decision
```

## Regression

Every previously discovered bug gets a permanent regression test.

## Property tests where useful

Examples:

``` text
mastery always remains 0..1
duplicate event cannot increase evidence twice
student A cannot affect student B
difficulty stays 1..5
invalid curriculum never loads successfully
```

------------------------------------------------------------------------

# 22. MANDATORY END-TO-END SCENARIOS

## Scenario A --- Beginner

``` text
Hess's Law mastery = 0.20
student gets two conceptual questions wrong
```

Expected:

``` text
misconception
↓
difficulty reduction
↓
remediation
↓
prerequisite review if required
↓
shorter review interval
```

## Scenario B --- Strong student

``` text
Hess's Law mastery = 0.88
two independent correct answers
```

Expected:

``` text
difficulty increase
↓
no unnecessary remediation
↓
delayed review scheduled
```

## Scenario C --- Hint dependency

Expected:

``` text
hint-supported success
→ slower mastery growth
→ independent recall scheduled
```

## Scenario D --- Retention failure

Expected:

``` text
previously strong concept
↓
delayed review failure
↓
review interval shortened
↓
practice returned
```

## Scenario E --- Cross-domain

``` text
Thermodynamics mastery = 0.80
no Inorganic evidence
```

Student asks:

``` text
Explain ionization enthalpy.
```

Expected:

``` text
Inorganic Chemistry
```

and no Thermodynamics mastery mutation.

## Scenario F --- Cross-student

``` text
A: Hess = 0.90
B: Hess = 0.20
```

Expected adaptive decisions must differ because their persisted evidence
differs.

------------------------------------------------------------------------

# 23. NEW-BUG DISCOVERY PROTOCOL

During the re-audit, the agent must actively search for bugs beyond the
previous list.

Inspect:

``` text
race conditions
state inconsistencies
stale caches
incorrect defaults
null handling
empty data
partial responses
model timeouts
RAG empty results
database retries
duplicate events
session restoration
browser refresh
multiple tabs
mode switching
concurrent students
malformed model JSON
invalid question records
curriculum corruption
```

For every new bug create:

``` text
BUG-NEW-001
BUG-NEW-002
...
```

Format:

``` yaml
id: BUG-NEW-001
severity: P0|P1|P2|P3
component:
status: OPEN
description:
reproduction:
root_cause:
fix:
regression_test:
```

------------------------------------------------------------------------

# 24. REGRESSION PREVENTION

Every fixed P0/P1 issue MUST have a regression test.

Required mapping:

``` text
P0-01 → adaptive integration test
P0-02 → evaluator regression suite
P0-03 → concept resolution tests
P0-04 → learner-state tests
P0-05 → concurrency/idempotency tests
P0-06 → mastery property tests
P0-07 → prerequisite validation tests
P0-08 → curriculum schema tests
P0-09 → multi-student isolation tests
P0-10 → mode isolation tests
```

------------------------------------------------------------------------

# 25. PROGRESS TRACKER

Create/update:

``` text
PROGRESS_TRACKER.yaml
```

Use this exact structure:

``` yaml
project: Gayatri Tutor Chemistry
status: IN_PROGRESS

current_phase: 0
current_task: P0-01

last_completed_task: null
last_verified_commit: null

audit:
  previous_audit_date: null
  current_audit_date: "2026-09-19"

baseline:
  python_version: null
  git_commit: null
  branch: null
  dirty_worktree: null
  tests_passed: null
  tests_failed: null
  tests_skipped: null

previous_findings:
  P0-01_adaptive_state: TODO
  P0-02_evaluator: TODO
  P0-03_hardcoded_topic: TODO
  P0-04_memory: TODO
  P0-05_streaming_race: TODO
  P0-06_mastery: TODO
  P0-07_prerequisites: TODO
  P0-08_stable_ids: TODO
  P0-09_student_scope: TODO
  P0-10_mode_isolation: TODO

new_bugs: []

phases:
  phase_0_reaudit: TODO
  phase_1_learning_state: TODO
  phase_2_evaluator: TODO
  phase_3_concept_resolution: TODO
  phase_4_adaptive_mastery: TODO
  phase_5_misconceptions: TODO
  phase_6_spaced_review: TODO
  phase_7_assessment: TODO
  phase_8_curriculum_validation: TODO
  phase_9_rag: TODO
  phase_10_concurrency: TODO
  phase_11_mode_isolation: TODO
  phase_12_progress: TODO
  phase_13_silent_failures: TODO
  phase_14_database: TODO
  phase_15_security: TODO
  phase_16_model_config: TODO
  phase_17_tests: TODO

adaptive_learning:
  student_scoped_mastery: TODO
  learning_events: TODO
  evaluator: TODO
  active_concept: TODO
  mastery_engine: TODO
  difficulty_policy: TODO
  misconceptions: TODO
  spaced_review: TODO
  assessment: TODO
  progress: TODO

tests:
  unit: TODO
  integration: TODO
  regression: TODO
  concurrency: TODO
  security: TODO
  curriculum: TODO

last_session:
  date: null
  summary: null
  files_changed: []
  tests_run: []
  tests_passed: []
  tests_failed: []
  blockers: []

next_action: >
  Run Phase 0 repository re-audit and verify every previous finding
  against the current checkout before changing implementation.
```

------------------------------------------------------------------------

# 26. SESSION RESUME RULE

If the agent stops halfway through a phase:

``` text
DO NOT restart the phase blindly.
```

Read:

``` text
PROGRESS_TRACKER.yaml
```

Then:

``` text
1. inspect last verified commit
2. inspect files_changed
3. inspect tests_run
4. rerun failed tests
5. continue from current_task
```

If code state is uncertain:

``` text
git diff
git status
pytest relevant tests
```

before modifying anything.

------------------------------------------------------------------------

# 27. PHASE COMPLETION REPORT

At the end of every phase, append:

``` markdown
## Phase N Completion Report

### Status
DONE | PARTIAL | BLOCKED | FAILED

### Tasks completed
- ...

### Files changed
- ...

### Tests
- Command:
- Passed:
- Failed:
- Skipped:

### Bugs fixed
- ...

### New bugs discovered
- ...

### Architecture changes
- ...

### Remaining risks
- ...

### Next phase
- ...
```

------------------------------------------------------------------------

# 28. FINAL RELEASE GATE

Do not call the repository production-ready until:

``` text
[ ] Fresh re-audit completed
[ ] All previous findings classified
[ ] All P0 issues fixed
[ ] All P0 regression tests pass
[ ] P1 issues resolved or explicitly documented
[ ] Student state isolated
[ ] Evaluator reliable
[ ] Active concept dynamic
[ ] Adaptive policy evidence-driven
[ ] Misconceptions persisted
[ ] Spaced review functional
[ ] Assessment functional
[ ] Curriculum validated
[ ] RAG failures observable
[ ] Streaming race eliminated
[ ] General/Chemistry isolation verified
[ ] Progress derived from persisted learning state
[ ] Silent failure audit completed
[ ] Database migration verified
[ ] Security tests pass
[ ] Model configuration consistent
[ ] Full test suite passes
[ ] Documentation matches implementation
[ ] Tracker shows all phases complete
```

------------------------------------------------------------------------

# 29. FINAL ARCHITECTURAL INVARIANT

The final implementation must preserve:

``` text
                    ┌───────────────────────┐
                    │   STUDENT EVIDENCE    │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │   ANSWER EVALUATION   │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │   LEARNING EVENT      │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │ STUDENT LEARNING      │
                    │ STATE / MASTERY       │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │ ADAPTIVE POLICY       │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │ NEXT LEARNING ACTION  │
                    └───────────┬───────────┘
                                ↓
                    ┌───────────────────────┐
                    │ TUTOR RESPONSE        │
                    └───────────┬───────────┘
                                │
                                └──────────→ NEW EVIDENCE
```

The LLM generates tutoring content.

It must NOT be the authoritative owner of:

``` text
student mastery
assessment score
learning history
prerequisite state
review schedule
student identity
```

Those belong to deterministic application state and persisted evidence.

------------------------------------------------------------------------

# 30. FIRST COMMAND TO THE LOCAL AGENT

The agent should begin with:

``` text
Read:
- this file
- README.md
- PROGRESS_TRACKER.yaml if present
- recent git history
- current tests

Then:

1. Run the baseline test suite.
2. Build the architecture map.
3. Reverify P0-01 through P0-10.
4. Search for new regressions/bugs.
5. Create AUDIT_REVERIFICATION.md.
6. Update PROGRESS_TRACKER.yaml.
7. DO NOT implement Phase 1 until Phase 0 has evidence.
```

The agent's first objective is therefore **not to write code**.

It is to establish the truth about the current repository.

Only after that should it begin fixing the system.
