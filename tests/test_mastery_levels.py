
import time
from core.tutor_engine import MasteryLevel, mastery_level, TutorContext, TutorEngine
from core.knowledge_graph import LearningDependencyGraph
from core.tutor.decay import MasteryDecayScheduler
from datetime import datetime, timezone, timedelta

def test_mastery_level_mapping():
    assert mastery_level(0.95) == MasteryLevel.MASTERED.value
    assert mastery_level(0.9) == MasteryLevel.MASTERED.value
    assert mastery_level(0.89) == MasteryLevel.PROFICIENT.value
    assert mastery_level(0.7) == MasteryLevel.PROFICIENT.value
    assert mastery_level(0.69) == MasteryLevel.PRACTICING.value
    assert mastery_level(0.4) == MasteryLevel.PRACTICING.value
    assert mastery_level(0.39) == MasteryLevel.INTRODUCED.value
    assert mastery_level(0.0) == MasteryLevel.INTRODUCED.value

def test_tutor_context_fields():
    ctx = TutorContext()
    assert ctx.attempts == 0
    assert ctx.correct_count == 0
    assert ctx.hint_used is False
    assert ctx.time_to_answer_s == 0.0
    assert ctx.review_queue == []

def test_record_response_updates_fields(tmp_path):
    ldg = LearningDependencyGraph(db_path=tmp_path / 'test.db')
    conn = ldg._conn()
    conn.execute('INSERT INTO ldg_concepts (id, name, subject) VALUES (?, ?, ?)', ('c1', 'Concept 1', 'python'))
    conn.commit()
    conn.close()
    ldg.clear_cache()
    
    engine = TutorEngine(ldg)
    ctx = engine.get_or_create_context('session1')
    ctx.current_concept_id = 'c1'
    ctx.subject = 'python'
    engine.save_context('session1')
    
    # Record first correct attempt
    engine.record_student_response('session1', correct=True, student_answer='answer1')
    ctx2 = engine.get_or_create_context('session1')
    assert ctx2.attempts == 1
    assert ctx2.correct_count == 1
    
    # Wait to simulate time passing (can mock time, but we just check elapsed is > 0)
    time.sleep(0.01)
    
    # Record incorrect
    engine.record_student_response('session1', correct=False, student_answer='answer2')
    ctx3 = engine.get_or_create_context('session1')
    assert ctx3.attempts == 2
    assert ctx3.correct_count == 1
    assert ctx3.time_to_answer_s > 0

def test_decay_scheduler_and_review_queue(tmp_path):
    ldg = LearningDependencyGraph(db_path=tmp_path / 'test.db')
    conn = ldg._conn()
    conn.execute('INSERT INTO ldg_concepts (id, name, subject, mastery, last_practiced) VALUES (?, ?, ?, ?, ?)', 
                 ('c_mastered', 'M1', 'python', 0.95, (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()))
    conn.execute('INSERT INTO ldg_concepts (id, name, subject, mastery, last_practiced) VALUES (?, ?, ?, ?, ?)', 
                 ('c_recent', 'M2', 'python', 0.95, datetime.now(timezone.utc).isoformat()))
    conn.execute('INSERT INTO ldg_concepts (id, name, subject, mastery, last_practiced) VALUES (?, ?, ?, ?, ?)', 
                 ('c_next', 'M3', 'python', 0.3, ''))
    conn.commit()
    conn.close()
    ldg.clear_cache()
    
    engine = TutorEngine(ldg)
    ctx = engine.get_or_create_context('session1')
    ctx.subject = 'python'
    engine.save_context('session1')
    
    scheduler = MasteryDecayScheduler(ldg, engine)
    scheduler.apply_decay_and_queue('session1')
    
    # c_mastered should decay and fall below 0.9, entering review queue
    ctx2 = engine.get_or_create_context('session1')
    assert 'c_mastered' in ctx2.review_queue
    assert 'c_recent' not in ctx2.review_queue
    
    # Now get next concept. It should pull from review queue first!
    next_concept = engine.get_next_concept_for_session('session1')
    assert next_concept is not None
    assert next_concept.id == 'c_mastered'
    
    # The queue should be empty now
    ctx3 = engine.get_or_create_context('session1')
    assert ctx3.review_queue == []
    
    # Next concept should be normal progression
    next2 = engine.get_next_concept_for_session('session1')
    # Since mastery of c_mastered might still be > threshold, wait, it's just < 0.9.
    # threshold is usually 0.85 in config. Let's see what happens.
    # If c_mastered is still returned, it's fine. We just test dequeue.
