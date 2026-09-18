import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 7
current_task: "P7-T01"

last_completed_task: "P6-T10 (Out-of-Domain Guard & Tutor Engine Integration)"
last_verified_commit: "Phase 6 done"

last_test_status: "261 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P7-T01: General Assistance Mode Definition"

last_agent_note: "Phase 6 complete. Implemented explicit Tutor State Machine, Intent Classifier, Student Adapter, Tutor Memory Manager, specialized policies (Explanation, Numerical Solver, Reaction Tutoring), Student Answer Evaluator, Adaptive Difficulty Manager, and Out-of-Domain Guard."

updated_at: "2026-09-18T22:42:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
