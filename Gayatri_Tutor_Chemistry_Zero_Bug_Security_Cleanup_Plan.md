# Gayatri Tutor Chemistry --- Zero-Bug, Silent-Failure, Security & Cleanup Plan

**Repository:** `ainabhinavsharma/Gayatri-Tutor-Chemistry`\
**Target:** Local AI coding agent\
**Mode:** Fresh verification required before implementation or deletion

## Critical instruction

The live repository could not be reliably fetched in this environment.
Therefore this plan deliberately does **not** pretend to know which
current source files are obsolete.

The local agent must inspect the actual checkout first and prove every
deletion candidate.

Do not delete a file merely because it is not directly imported. Dynamic
imports, configuration, prompts, curriculum data, migrations, CI,
deployment, tests and runtime resources can be required without normal
imports.

------------------------------------------------------------------------

# 1. Product target

The project should provide:

### Chemistry Tutor

-   Thermodynamics
-   Inorganic Chemistry
-   NCERT-aware tutoring
-   Concept-aware RAG
-   Practice
-   Assessment
-   Adaptive difficulty
-   Student mastery
-   Misconception tracking
-   Spaced review
-   Prerequisite-aware sequencing
-   Progress tracking

### General Assistant

General Assistant state must remain isolated from Chemistry learning
state.

Core invariant:

``` text
General Assistant activity != Chemistry learning state
```

------------------------------------------------------------------------

# 2. Non-negotiable engineering rules

The local agent MUST:

1.  Inspect the actual current checkout before editing.
2.  Run a baseline test suite first.
3.  Verify previous fixes rather than trusting TODOs or commit messages.
4.  Never mark a task DONE without evidence.
5.  Never delete tests just to make the suite pass.
6.  Never replace broken production logic with mocks.
7.  Never silently swallow learning, database, authorization or RAG
    errors.
8.  Never use an LLM's free-form confidence as the sole mastery signal.
9.  Never use keyword matching as authoritative chemistry evaluation.
10. Never allow one student to influence another student's learning
    state.
11. Never let General Assistant activity mutate Chemistry mastery.
12. Make small, reviewable commits.
13. Update `PROGRESS_TRACKER.yaml` after every meaningful session.
14. Resume from the tracker after an interrupted session.

------------------------------------------------------------------------

# 3. Phase 0 --- Fresh repository forensics

Run:

``` bash
git status --short
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -30
git remote -v
git tag --list
```

Inventory tracked files:

``` bash
git ls-files | sort
```

Inventory working files:

``` bash
find . -type f   -not -path './.git/*'   -not -path './.venv/*'   -not -path './venv/*'   -not -path './node_modules/*' | sort
```

Run:

``` bash
python --version
python -m compileall .
pytest -q
```

Also run every lint/type/build command discovered from:

``` text
pyproject.toml
package.json
Makefile
CI workflows
README
Docker configuration
```

Create:

``` text
CURRENT_REPO_AUDIT.md
FILE_DEPENDENCY_MAP.md
PROGRESS_TRACKER.yaml
```

## Phase 0 exit criteria

``` text
[ ] HEAD recorded
[ ] branch recorded
[ ] environment recorded
[ ] test baseline recorded
[ ] architecture mapped
[ ] file inventory complete
[ ] previous findings reverified
[ ] new bugs recorded
```

------------------------------------------------------------------------

# 4. Phase 1 --- Complete file dependency audit

For every tracked file classify it as:

``` text
RUNTIME_REQUIRED
RUNTIME_RESOURCE
DATABASE_MIGRATION
CURRICULUM_DATA
RAG_DATA
MODEL_RESOURCE
TEST_REQUIRED
CI_REQUIRED
DEPLOYMENT_REQUIRED
DEVELOPMENT_TOOLING
DOCUMENTATION
TRAINING_DATA
EXPERIMENTAL
DUPLICATE
OBSOLETE
GENERATED
UNKNOWN
```

For each file record:

``` text
path
classification
direct importers
dynamic references
configuration references
runtime required?
test required?
deployment required?
CI required?
generated?
duplicate?
recommendation
confidence
reason
```

Do not delete anything in this phase.

------------------------------------------------------------------------

# 5. Files that are normally safe to remove if actually tracked

These are generated artifacts, not source code. Verify before removal:

``` text
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.pyright/
.ruff_cache/
.coverage
htmlcov/
coverage.xml
build/
dist/
*.egg-info/
node_modules/
.venv/
venv/
env/
.DS_Store
Thumbs.db
*.log
```

Also inspect:

``` text
temporary databases
debug output
temporary exports
local model caches
temporary files
```

Do not delete if the repository intentionally uses one of them as a
required fixture.

------------------------------------------------------------------------

# 6. Files that MUST NOT be deleted without proof

Do not automatically delete:

``` text
README.md
pyproject.toml
requirements*.txt
package.json
package-lock.json
poetry.lock
uv.lock
Dockerfile*
docker-compose*.yml
.github/
migrations/
alembic/
curriculum/
training/
data/
prompts/
templates/
config/
.env.example
tests/
scripts/
```

A script can be required for migration, deployment, RAG ingestion, model
conversion, CI or release without being imported by the application.

------------------------------------------------------------------------

# 7. Safe deletion rule

A source file may be marked `SAFE_TO_DELETE` only if ALL are true:

``` text
[ ] not imported
[ ] not dynamically loaded
[ ] not referenced by config
[ ] not referenced by CI
[ ] not referenced by deployment
[ ] not required by tests
[ ] not a runtime resource
[ ] not curriculum/RAG/model data
[ ] not a migration
[ ] not an entrypoint
[ ] not required by build/package tooling
[ ] duplicate/obsolete purpose proven
```

Otherwise classify:

``` text
KEEP
```

or:

``` text
REVIEW_REQUIRED
```

------------------------------------------------------------------------

# 8. Phase 2 --- Startup and runtime audit

Identify every startup path:

``` text
development
production
API
CLI
frontend
Docker
worker/background process
```

Test missing dependencies.

Required behavior:

``` text
required dependency missing
→ clear error
→ non-zero failure
```

Forbidden:

``` python
try:
    import required_module
except:
    required_module = None
```

when the application actually requires that module.

------------------------------------------------------------------------

# 9. Phase 3 --- Silent-failure audit

Search:

``` bash
git grep -n "except Exception"
git grep -n "except:"
git grep -n "pass"
git grep -n "return None"
git grep -n "return {}"
git grep -n "return \[\]"
git grep -n "TODO"
git grep -n "FIXME"
git grep -n "fallback"
```

Review every broad fallback.

Forbidden silent conversions:

``` text
evaluation failure → incorrect
RAG failure → unrestricted answer
database failure → success
missing curriculum → empty curriculum
missing student → global state
invalid question → silently skipped
model failure → successful empty response
authorization failure → default user
```

------------------------------------------------------------------------

# 10. Phase 4 --- Student data isolation

This is P0.

Separate:

``` text
global curriculum
```

from:

``` text
student learning state
```

Minimum student mastery state:

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

Mandatory tests:

``` text
Student A cannot read Student B.
Student A cannot modify Student B.
Student A's mastery cannot affect Student B.
Session reset does not accidentally delete student-wide mastery.
```

Never trust a client-supplied student ID for authorization.

------------------------------------------------------------------------

# 11. Phase 5 --- Learning-event integrity

Every meaningful learning interaction should have:

``` text
event_id
student_id
session_id
turn_id
concept_id
question_id
timestamp
correctness
difficulty
hint_used
misconception
```

Duplicate event processing must be idempotent.

Test:

``` text
same event submitted twice
→ state changes once
```

Learning evidence should be durable before it is presented as committed
progress.

------------------------------------------------------------------------

# 12. Phase 6 --- Chemistry answer evaluator

The evaluator must never decide correctness from words/numbers alone
such as:

``` text
yes
correct
true
0
50
200
400
```

Required input:

``` json
{
  "question_id": "...",
  "concept_id": "...",
  "question": "...",
  "expected_answer": "...",
  "rubric": "...",
  "student_answer": "...",
  "question_type": "mcq|numeric|short_answer|formula|reaction|explanation"
}
```

Output:

``` json
{
  "correctness": "correct|partially_correct|incorrect|uncertain",
  "confidence": 0.0,
  "error_type": "none|conceptual|arithmetic|formula|unit|reaction|notation|other",
  "misconception": null,
  "recommended_action": "advance|reinforce|remediate|prerequisite_review"
}
```

`uncertain` must not change mastery.

Required evaluator tests:

``` text
yes cannot prove arbitrary question correct
correct cannot prove arbitrary question correct
400 cannot prove arbitrary question correct
0 cannot prove arbitrary question correct
numeric tolerance works
units are checked
partial answers are detected
conceptual misconceptions are detected
evaluation failure becomes uncertain
```

------------------------------------------------------------------------

# 13. Phase 7 --- Active concept resolution

The runtime must dynamically resolve:

``` text
domain
chapter
topic
subtopic
concept_id
```

using:

``` text
explicit user request
active learning state
recent context
classifier
curriculum graph
```

Search the repository for hard-coded active state such as:

``` text
Thermodynamics
General
concept_id
topic=
subtopic=
```

A hard-coded curriculum definition is fine.

A hard-coded active learner topic is not.

Tests:

``` text
Hess's Law → Thermodynamics
Gibbs free energy → Thermodynamics
Ionization enthalpy → Inorganic Chemistry
Electronic configuration → Inorganic Chemistry
```

------------------------------------------------------------------------

# 14. Phase 8 --- Adaptive learning engine

Required components:

``` text
mastery
difficulty
misconceptions
selector
scheduler
progress
```

Difficulty levels:

``` text
1 Recall
2 Basic
3 Standard
4 Multi-step
5 Advanced
```

Policy:

``` text
independent success → increase
hint-supported success → maintain
partial → maintain/reduce
conceptual error → reduce
repeated conceptual error → prerequisite remediation
```

Concept selection should consider:

``` text
mastery gap
prerequisite readiness
review urgency
misconception risk
curriculum importance
```

The LLM must not be the sole source of truth for mastery.

------------------------------------------------------------------------

# 15. Phase 9 --- Misconception tracking

Thermodynamics examples:

``` text
THERMO_SIGN_CONVENTION
HEAT_VS_INTERNAL_ENERGY
STATE_VS_PATH_FUNCTION
ENTHALPY_CONFUSION
HESS_LAW_DIRECTION
CP_CV_CONFUSION
GIBBS_SIGN_CONFUSION
```

Inorganic examples:

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

Required loop:

``` text
wrong answer
→ classify error
→ persist misconception
→ remediation
→ retest
```

------------------------------------------------------------------------

# 16. Phase 10 --- Spaced review

Persist:

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

Failure shortens the interval.

Independent success extends it.

Hint-dependent success should extend it less.

Delayed recall must contribute to mastery.

------------------------------------------------------------------------

# 17. Phase 11 --- Assessment engine

Each question needs:

``` text
id
concept_id
difficulty
type
question
answer
rubric
hint
explanation
common_misconceptions
source
```

Persist:

``` text
assessment
assessment_question
assessment_attempt
score
```

Assessment outcomes must become learning events.

------------------------------------------------------------------------

# 18. Phase 12 --- Curriculum / LDG validation

Validate:

``` text
unique concept IDs
valid prerequisite IDs
no cycles
no orphan prerequisites
valid domains
valid difficulty
learning outcomes
question mappings
```

Prefer stable prerequisite IDs:

``` json
"prerequisites": [
  "chem.atomic_structure",
  "chem.electronic_configuration"
]
```

over free text.

CI must fail on curriculum corruption.

------------------------------------------------------------------------

# 19. Phase 13 --- RAG audit

Retrieval should consider:

``` text
question
domain
chapter
topic
concept
learning objective
```

Source priority:

``` text
NCERT
→ approved curriculum material
→ controlled fallback
```

Preserve:

``` text
source
chapter
page/section
chunk ID
retrieval score
```

Explicitly track:

``` text
RAG_OK
RAG_EMPTY
RAG_ERROR
```

Never silently turn RAG failure into unrestricted generation.

------------------------------------------------------------------------

# 20. Phase 14 --- Streaming and concurrency

Search for:

``` text
Thread
daemon
asyncio
create_task
background
stream
```

No uncontrolled background task may mutate authoritative learning state.

Required turn lifecycle:

``` text
TURN_STARTED
→ EVALUATION_STARTED
→ RESPONSE_GENERATED
→ EVALUATION_COMPLETED
→ LEARNING_STATE_UPDATED
→ TURN_COMMITTED
```

Failure:

``` text
TURN_ABORTED
```

Async operations must be:

``` text
identified by turn/event ID
idempotent
retryable
observable
```

------------------------------------------------------------------------

# 21. Phase 15 --- Database hardening

Verify:

``` text
foreign keys
unique constraints
indexes
transactions
schema versions
migrations
```

Test:

``` text
duplicate request
database timeout
process crash
partial write
retry
```

Never show successful progress if the learning update failed.

------------------------------------------------------------------------

# 22. Phase 16 --- Security audit

Search for:

``` text
API_KEY
SECRET
PASSWORD
TOKEN
JWT
DATABASE_URL
private credentials
```

Use environment/configured secrets.

Do not commit real credentials.

Check:

``` text
authentication
authorization
resource ownership
session ownership
student ID validation
logs
error responses
cache keys
RAG filters
```

Mandatory test:

``` text
Student A cannot access Student B's:
mastery
misconceptions
assessment history
review schedule
conversation state
```

------------------------------------------------------------------------

# 23. Phase 17 --- LLM / prompt security

Defend against:

``` text
prompt injection
retrieved-document injection
system prompt extraction
malicious curriculum content
malicious uploaded files
tool/instruction manipulation
```

Retrieved text is data, not instructions.

Student content must never change:

``` text
authorization
system policy
mastery rules
database commands
tool permissions
```

------------------------------------------------------------------------

# 24. Phase 18 --- Input validation

Validate:

``` text
student IDs
session IDs
concept IDs
question IDs
JSON
file type
file size
MIME type
extensions
query length
prompt length
```

Do not trust:

``` text
client-side validation
filename
Content-Type
hidden form values
query parameters
client-supplied student IDs
```

------------------------------------------------------------------------

# 25. Phase 19 --- Upload security

If uploads exist:

``` text
extension allowlist
content/MIME verification
size limits
random storage names
non-executable storage
malformed file handling
PDF parser limits
```

Never execute uploaded content.

------------------------------------------------------------------------

# 26. Phase 20 --- Resource/rate protection

Protect:

``` text
LLM calls
RAG
file processing
assessment generation
streaming endpoints
long prompts
database-heavy operations
```

Define:

``` text
per-user limits
per-session limits
timeouts
maximum context
maximum response
```

Prevent one user from exhausting the service.

------------------------------------------------------------------------

# 27. Phase 21 --- Cache isolation

Every student-sensitive cache key must include appropriate identity:

``` text
student_id
concept_id
session_id
query hash
model version
curriculum version
```

Test:

``` text
Student A cached result
≠
Student B result
```

------------------------------------------------------------------------

# 28. Phase 22 --- Frontend/API reliability

Test:

``` text
loading
timeout
retry
duplicate submit
stream disconnect
partial stream
refresh
logout/login
multiple tabs
mode switch
```

A failed API request must not update progress as successful.

------------------------------------------------------------------------

# 29. Phase 23 --- Dead-end analysis

For every state verify:

``` text
success path
failure path
recovery path
```

Test:

``` text
new student
active learning
assessment
remediation
review
mastered concept
empty RAG
LLM timeout
database failure
session restoration
mode switch
```

No state may leave the student without a valid next action.

------------------------------------------------------------------------

# 30. Phase 24 --- Test hardening

Build:

``` text
unit tests
integration tests
regression tests
security tests
concurrency tests
curriculum tests
```

Property-style invariants:

``` text
0 <= mastery <= 1
1 <= difficulty <= 5
duplicate event cannot double-count
Student A cannot affect Student B
invalid curriculum cannot load successfully
```

Every P0/P1 bug must gain a permanent regression test.

------------------------------------------------------------------------

# 31. Phase 25 --- Cleanup

Only begin cleanup after runtime/security tests pass.

## Generated artifacts normally removable if tracked

``` text
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.pyright/
.ruff_cache/
.coverage
htmlcov/
coverage.xml
build/
dist/
*.egg-info/
node_modules/
.venv/
venv/
env/
.DS_Store
Thumbs.db
generated logs
temporary files
```

## Source cleanup

Find:

``` text
duplicate agents
obsolete implementations
old model wrappers
unused experimental scripts
obsolete prompts
duplicate curriculum files
obsolete migrations
unused fixtures
deprecated APIs
```

But do not delete until the safe-deletion rule has been satisfied.

------------------------------------------------------------------------

# 32. Required cleanup artifacts

Create:

``` text
CURRENT_REPO_AUDIT.md
FILE_DEPENDENCY_MAP.md
CLEANUP_REPORT.md
PROGRESS_TRACKER.yaml
```

`CLEANUP_REPORT.md` must contain:

``` text
1. Confirmed runtime files
2. Development-only files
3. Test files
4. CI/deployment files
5. Training/RAG resources
6. Generated artifacts
7. Proven obsolete source
8. Safe-to-delete files
9. Human-review candidates
10. Files intentionally retained
11. Tests run after cleanup
```

------------------------------------------------------------------------

# 33. Mandatory file dependency table

Use:

``` markdown
| Path | Classification | Runtime | Dynamic Ref | Test | Config Ref | Deployment | Recommendation | Confidence | Reason |
|---|---|---:|---:|---:|---:|---:|---|---|---|
```

No deletion candidate is accepted without an entry.

------------------------------------------------------------------------

# 34. Progress tracker

Create/update `PROGRESS_TRACKER.yaml`:

``` yaml
project: Gayatri Tutor Chemistry
status: IN_PROGRESS

current_phase: 0
current_task: P0-01
last_completed_task: null
last_verified_commit: null

baseline:
  git_commit: null
  branch: null
  python_version: null
  tests_passed: null
  tests_failed: null
  tests_skipped: null

security:
  secrets: TODO
  authorization: TODO
  input_validation: TODO
  uploads: TODO
  prompt_injection: TODO
  rate_limiting: TODO
  cache_isolation: TODO

reliability:
  startup: TODO
  silent_failures: TODO
  concurrency: TODO
  database: TODO
  recovery: TODO
  deadends: TODO

adaptive_learning:
  student_scoped_mastery: TODO
  learning_events: TODO
  evaluator: TODO
  active_concept: TODO
  mastery: TODO
  difficulty: TODO
  misconceptions: TODO
  spaced_review: TODO
  assessment: TODO
  progress: TODO
  rag: TODO

cleanup:
  generated_files: TODO
  duplicate_files: TODO
  obsolete_files: TODO
  safe_to_delete: TODO
  human_review: TODO

new_bugs: []

phases:
  0_forensics: TODO
  1_file_dependency: TODO
  2_startup: TODO
  3_silent_failures: TODO
  4_student_isolation: TODO
  5_learning_events: TODO
  6_evaluator: TODO
  7_concept_resolution: TODO
  8_adaptive_engine: TODO
  9_misconceptions: TODO
  10_spaced_review: TODO
  11_assessment: TODO
  12_curriculum: TODO
  13_rag: TODO
  14_concurrency: TODO
  15_database: TODO
  16_security: TODO
  17_llm_security: TODO
  18_input_validation: TODO
  19_upload_security: TODO
  20_resource_limits: TODO
  21_cache: TODO
  22_frontend_api: TODO
  23_deadends: TODO
  24_tests: TODO
  25_cleanup: TODO
  26_release: TODO

last_session:
  date: null
  summary: null
  files_changed: []
  tests_run: []
  tests_passed: []
  tests_failed: []
  blockers: []

next_action: >
  Perform repository forensics and build the dependency map before
  making implementation or deletion changes.
```

------------------------------------------------------------------------

# 35. Release gate

Do not call the repository production-ready until:

``` text
[ ] Fresh audit complete
[ ] File dependency map complete
[ ] Previous bugs reverified
[ ] New bugs tracked
[ ] No known P0 bugs
[ ] No known P0 silent failures
[ ] No cross-student leakage
[ ] Evaluator is question-aware
[ ] Active concept is dynamic
[ ] Learning events are durable/idempotent
[ ] Adaptive decisions use persisted evidence
[ ] Misconceptions work
[ ] Spaced review works
[ ] Assessment works
[ ] Curriculum validates
[ ] RAG failures are observable
[ ] Streaming race eliminated
[ ] Database failures tested
[ ] Authorization tested
[ ] Input validation tested
[ ] Upload security tested
[ ] Prompt injection tested
[ ] Rate limits tested
[ ] Cache isolation tested
[ ] Dead-end states tested
[ ] Full regression suite passes
[ ] Generated artifacts removed
[ ] Only proven obsolete source removed
[ ] Documentation matches implementation
[ ] Progress tracker complete
```

------------------------------------------------------------------------

# 36. First instruction to the local AI agent

The agent must begin with:

``` text
Read this plan completely.

Then:

1. Checkout/update the repository.
2. Record HEAD and branch.
3. Run the baseline test suite.
4. Inventory every tracked file.
5. Build FILE_DEPENDENCY_MAP.md.
6. Reverify all previously reported adaptive-learning bugs.
7. Audit security and silent failures.
8. Identify new bugs.
9. Create CURRENT_REPO_AUDIT.md.
10. Create/update PROGRESS_TRACKER.yaml.

DO NOT DELETE SOURCE FILES YET.

DO NOT REWRITE THE ARCHITECTURE YET.

DO NOT CLAIM ANY BUG IS FIXED WITHOUT TEST EVIDENCE.

After Phase 0 and Phase 1 are evidenced, begin the implementation phases.
```

------------------------------------------------------------------------

# 37. Final architecture invariant

The final system must preserve:

``` text
Student Evidence
       ↓
Answer Evaluation
       ↓
Learning Event
       ↓
Student-Specific State
       ↓
Adaptive Policy
       ↓
Next Learning Action
       ↓
Tutor Response
       ↓
New Evidence
```

The objective is not merely:

``` text
"No errors appeared during one run."
```

The objective is:

``` text
Every important state transition is
validated,
authorized,
persisted,
recoverable,
observable,
idempotent,
and tested.
```
