
import json
import logging
from pathlib import Path
from core.knowledge_graph import LearningDependencyGraph

logger = logging.getLogger('gayatri.curriculum')

class CurriculumProvider:
    def __init__(self, subject: str, board: str = 'default', grade: str = 'default', 
                 language: str = 'en', version: str = 'v1'):
        self.subject = subject
        self.board = board
        self.grade = grade
        self.language = language
        self.version = version
        
        # Determine paths
        # Data is in data/curriculum/<subject>/<grade>.json (simple convention for now)
        base_dir = Path(__file__).parent.parent.parent / 'data' / 'curriculum'
        # Special case python beginner for now
        if subject == 'python' and grade == 'beginner':
            self.file_path = base_dir / 'python' / 'beginner.json'
        else:
            self.file_path = base_dir / subject / f'{grade}.json'

    def load_into(self, graph: LearningDependencyGraph) -> int:
        if not self.file_path.exists():
            logger.error(f'Curriculum file not found: {self.file_path}')
            return 0
            
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        concepts_added = 0
        for concept_data in data.get('concepts', []):
            graph.add_concept(
                concept_id=concept_data['id'],
                name=concept_data['name'],
                description=concept_data.get('description', ''),
                difficulty=concept_data.get('difficulty', 0.5),
                subject=data.get('subject', self.subject),
                minimum_mastery=concept_data.get('minimum_mastery', 0.85),
                evidence_count=concept_data.get('evidence_count', 3),
                assessment_types=concept_data.get('assessment_types', [])
            )
            concepts_added += 1

        for concept_data in data.get('concepts', []):
            concept_id = concept_data['id']
            for prereq_id in concept_data.get('prerequisites', []):
                graph.add_prerequisite(concept_id, prereq_id)

        logger.info(f'Loaded curriculum {self.subject} ({self.grade}): {concepts_added} concepts')
        return concepts_added
        
    @staticmethod
    def list_subjects() -> list[str]:
        # For now, just a hardcoded list or scan directories
        base_dir = Path(__file__).parent.parent.parent / 'data' / 'curriculum'
        if not base_dir.exists():
            return []
        
        subjects = []
        for d in base_dir.iterdir():
            if d.is_dir():
                subjects.append(d.name)
        return subjects
