import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 6
current_task: "P6-T01"

last_completed_task: "P5-T07 (RAG Evaluation & Integration)"
last_verified_commit: "Phase 5 done"

last_test_status: "245 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P6-T01: Chemistry Tutor State Machine"

last_agent_note: "Phase 5 complete. Implemented NCERT source manifest, document ingester, SQLite RAG chunk store, hybrid retrieval with confidence scoring (HIGH/MEDIUM/LOW), strict citation formatting, and prompt injection in ChemistryTutorRuntime."

updated_at: "2026-09-18T22:24:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
