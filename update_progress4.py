import re

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''project: "Gayatri Tutor V3 -> Chemistry Tutor + General Assistance"

overall_status: "IN_PROGRESS"

current_phase: 5
current_task: "P5-T01"

last_completed_task: "P4-T05 (Dataset Topic Registry)"
last_verified_commit: "Phase 4 done"

last_test_status: "18/18 curriculum tests PASSED"
last_benchmark_status: "TTFT 1844ms (historical)"

known_failures: []
known_risks: []
blocked_tasks: []

next_action: "P5-T01: NCERT RAG Source Manifest"

last_agent_note: "Phase 4 complete. Curriculum manifest loaded and typed (CurriculumManifest, CurriculumDomain). KG seeded from manifest. Dataset topic registry bridges training topic_ids to curriculum. ChemistryTutorRuntime now injects live curriculum topics into system prompts."

updated_at: "2026-09-18T21:57:00+05:30"'''

content = re.sub(
    r'project: "Gayatri Tutor V3 -> Chemistry Tutor \+ General Assistance".*?updated_at: ".*?"',
    new_block,
    content,
    flags=re.DOTALL
)

with open('Gayatri_Tutor_V3_Chemistry_General_Assistance_Execution_Plan.md', 'w', encoding='utf-8') as f:
    f.write(content)
