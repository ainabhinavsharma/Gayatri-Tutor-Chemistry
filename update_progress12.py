import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 13
current_task: "P13-T01"

last_completed_task: "P12-T05 (Thread-Safe Cancellation & Governance)"
last_verified_commit: "Phase 12 done"

last_test_status: "303 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P13-T01: Final Performance Reconciliation & Sign-Off"

last_agent_note: "Phase 12 complete. Hardened QWebChannel PySide bridge slots, implemented server-side validate_app_mode(), verified background database persistence resilience, and verified thread-safe idempotent cancellation."

updated_at: "2026-09-19T01:27:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
