import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 8
current_task: "P8-T01"

last_completed_task: "P7-T10 (Assessment Anti-Leakage & Grader Engine)"
last_verified_commit: "Phase 7 done"

last_test_status: "275 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P8-T01: General Assistant System Policy"

last_agent_note: "Phase 7 complete. Implemented typed Question schemas (MCQ, Numerical, Assertion-Reasoning, Reaction Completion, Equation Balancing), deterministic Chemical Equation Balancing Engine, backend Assessment Grader with anti-leakage protection, Chapter & Mock Test Generators, and Adaptive Question Selector."

updated_at: "2026-09-18T23:13:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
