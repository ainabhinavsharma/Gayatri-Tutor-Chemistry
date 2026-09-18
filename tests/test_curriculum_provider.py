
from core.curriculum.provider import CurriculumProvider
from core.knowledge_graph import LearningDependencyGraph

def test_curriculum_provider_loads_curriculum(tmp_path):
    ldg = LearningDependencyGraph(db_path=tmp_path / 'test.db')
    provider = CurriculumProvider(subject='python', grade='beginner')
    # Because we moved the json to data/curriculum/python/beginner.json, it should be loaded successfully.
    # Assuming there are concepts in it...
    count = provider.load_into(ldg)
    assert count > 0

    c = ldg.get_concept('python_variables')
    if c:
        assert c.minimum_mastery == 0.85
        assert c.evidence_count == 3
        
def test_list_subjects():
    subjects = CurriculumProvider.list_subjects()
    assert 'python' in subjects
