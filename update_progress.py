import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Update the progress block
new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 2
current_task: "P2-T01"

last_completed_task: "P1-T04 (Canonical runtime dispatch)"
last_verified_commit: "unknown (no git repo)"

last_test_status: "PASSED (237/237 tests - modified to mode logic)"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: ["No local git repository initialized"]
blocked_tasks: []

next_action: "P2-T01: Disable old agent registration"

last_agent_note: "Phase 1 complete. Core mode abstractions added (AppMode, ModePolicy). Orchestrator refactored to route strictly by mode, dispatching to ChemistryTutorRuntime or GeneralAssistantRuntime. Bridge updated to pass 'mode'."

updated_at: "2026-09-18T20:45:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
