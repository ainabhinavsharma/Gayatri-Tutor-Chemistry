import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 11
current_task: "P11-T01"

last_completed_task: "P10-T08 (Prompt Contracts & Inference Service Abstraction)"
last_verified_commit: "Phase 10 done"

last_test_status: "289 passed, 20 skipped, 0 failed"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P11-T01: Controlled Web Research Fallback Policy"

last_agent_note: "Phase 10 complete. Externalized versioned prompt contracts (chemistry_tutor_system_v1.txt, general_assistant_system_v1.txt), built PromptContractLoader, and unified inference routing via InferenceService."

updated_at: "2026-09-19T01:02:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
