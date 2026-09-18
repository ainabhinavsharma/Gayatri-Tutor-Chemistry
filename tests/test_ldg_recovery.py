
from core.tutor_engine import TutorEngine, RecoveryMode
from core.knowledge_graph import LearningDependencyGraph

def test_recovery_mode_normal(tmp_path):
    ldg = LearningDependencyGraph(db_path=tmp_path / 'test.db')
    ldg.add_concept('c1', 'Concept 1', subject='python')
    
    engine = TutorEngine(ldg)
    ctx = engine.get_or_create_context('session1')
    ctx.subject = 'python'
    engine.save_context('session1')
    
    next_c = engine.get_next_concept_for_session('session1')
    assert next_c is not None
    
    ctx = engine.get_or_create_context('session1')
    assert ctx.metadata.get('recovery_mode') == RecoveryMode.NORMAL.value

def test_recovery_mode_empty_curriculum(tmp_path):
    ldg = LearningDependencyGraph(db_path=tmp_path / 'test.db')
    
    engine = TutorEngine(ldg)
    ctx = engine.get_or_create_context('session1')
    ctx.subject = 'empty_subject'
    engine.save_context('session1')
    
    next_c = engine.get_next_concept_for_session('session1')
    assert next_c is None
    
    ctx = engine.get_or_create_context('session1')
    assert ctx.metadata.get('recovery_mode') == RecoveryMode.EMPTY_CURRICULUM.value

def test_recovery_mode_missing_prerequisites(tmp_path):
    ldg = LearningDependencyGraph(db_path=tmp_path / 'test.db')
    ldg.add_concept('c1', 'Concept 1 (Math)', subject='math')
    ldg.add_concept('c2', 'Concept 2 (Python)', subject='python')
    # Make python concept depend on unmastered math concept
    ldg.add_prerequisite('c2', 'c1')
    
    engine = TutorEngine(ldg)
    ctx = engine.get_or_create_context('session1')
    ctx.subject = 'python'
    engine.save_context('session1')
    
    # Next concept in python will be c2, but its prereq c1 is not mastered and not in subject
    # It will fall back to c2 (the only python candidate)
    next_c = engine.get_next_concept_for_session('session1')
    assert next_c is not None
    assert next_c.id == 'c2'
    
    ctx = engine.get_or_create_context('session1')
    assert ctx.metadata.get('recovery_mode') == RecoveryMode.MISSING_PREREQUISITES.value
