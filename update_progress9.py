import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 10
current_task: "P10-T01"

last_completed_task: "P9-T07 (Streaming UI & Two-Screen UI Architecture)"
last_verified_commit: "Phase 9 done"

last_test_status: "282 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P10-T01: Qwen Model Abstraction & Inference Service"

last_agent_note: "Phase 9 complete. Redesigned UI to Two-Screen UI Architecture with Home/Landing Screen mode cards (Chemistry Tutor & General Assistant), separate workspace views, isolated session histories per mode, first-run empty states, and user-friendly error formatting."

updated_at: "2026-09-19T00:43:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
