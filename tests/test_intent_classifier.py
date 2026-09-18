
import json
import pytest
from pathlib import Path
from core.agents.registry import agent_registry, AgentRegistry

@pytest.fixture(autouse=True)
def setup_registry():
    # Make sure default agents are loaded for testing
    from core.agents.default_agents import register_default_agents
    register_default_agents()
    yield

def test_routing_accuracy():
    fixture_path = Path('tests/fixtures/routing_cases.jsonl')
    assert fixture_path.exists(), 'Fixture file not found'
    
    correct = 0
    total = 0
    
    with open(fixture_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            case = json.loads(line)
            message = case['message']
            expected = case['expected_agent']
            
            result = agent_registry.dispatch(message)
            actual = result.primary.spec.name if result.primary else 'default'
            
            if actual == expected:
                correct += 1
            else:
                print(f'Failed: {message} -> Expected {expected}, got {actual}')
                
            total += 1
            
    accuracy = correct / total if total > 0 else 0
    assert accuracy >= 0.85, f'Accuracy {accuracy:.2%} is below 85%'

def test_ambiguous_detected():
    # Test ambiguous dispatch
    # Create two temporary agents with overlapping triggers
    test_registry = AgentRegistry()
    
    @test_registry.register(name='AgentA', triggers=['help with python', 'python code'])
    class AgentA: pass
    
    @test_registry.register(name='AgentB', triggers=['help with code', 'python code'])
    class AgentB: pass
    
    result = test_registry.dispatch('I need help with python code')
    assert result.is_ambiguous
    assert result.primary is None
    assert len(result.alternatives) == 2

def test_multi_intent_split():
    # Test multi intent detection
    result = agent_registry.dispatch('explain variables and then give me a practice problem')
    assert result.is_multi_intent

def test_command_always_wins():
    result = agent_registry.dispatch('/tutor I want to do web search')
    assert result.primary is not None
    assert result.primary.spec.name == 'Tutor'
    assert result.primary.confidence == 1.0
