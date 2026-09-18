import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 9
current_task: "P9-T01"

last_completed_task: "P8-T05 (General Assistant & Chemistry Mode Boundary)"
last_verified_commit: "Phase 8 done"

last_test_status: "279 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P9-T01: Two-Screen UI Navigation & Landing Screen"

last_agent_note: "Phase 8 complete. Implemented GeneralAssistantRuntime with general Q&A, writing/drafting, summarization, brainstorming, and explicit Chemistry Mode boundary detection with polite redirection."

updated_at: "2026-09-18T23:38:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
