import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 12
current_task: "P12-T01"

last_completed_task: "P11-T06 (Network Error Handling & Controlled Web Fallback)"
last_verified_commit: "Phase 11 done"

last_test_status: "299 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P12-T01: Security Audit & Governance Hardening"

last_agent_note: "Phase 11 complete. Implemented ResearchPolicy, ResearchFallbackEvaluator, WebPromptDefense (prompt injection defense), and WebResearchService with graceful network fallback."

updated_at: "2026-09-19T01:10:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
