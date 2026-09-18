
from pathlib import Path
from core.knowledge_graph import LearningDependencyGraph
from core.curriculum.provider import CurriculumProvider

def load_curriculum(graph: LearningDependencyGraph, curriculum_path: str | Path) -> int:
    path = Path(curriculum_path)
    # Basic shim mapping a direct path to a provider load
    import json
    with open(path) as f:
        data = json.load(f)
    
    subject = data.get('subject', 'unknown')
    # Use provider by manually setting its file path for this shim
    provider = CurriculumProvider(subject=subject, grade='unknown')
    provider.file_path = path
    return provider.load_into(graph)
