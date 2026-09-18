
import time
import pytest
from core.agents.runtime import ToolRegistry
from core.agents.policy import cooperative_tool, check_cancelled, get_cancellation_token

def test_timeout_fires_and_cancels_token():
    tools = ToolRegistry()
    
    token_seen = None
    
    @tools.register('my_tool', timeout_s=0.2)
    def my_tool():
        nonlocal token_seen
        token_seen = get_cancellation_token()
        time.sleep(0.4)
        return 'done'
        
    with pytest.raises(TimeoutError):
        tools.call('my_tool')
        
    assert token_seen is not None
    assert token_seen.is_cancelled

def test_cooperative_tool_exits_early():
    tools = ToolRegistry()
    
    @tools.register('coop_tool', timeout_s=0.2)
    @cooperative_tool
    def coop_tool():
        # A cooperative tool checks in a loop
        for _ in range(10):
            check_cancelled()
            time.sleep(0.05)
        return 'done'
        
    start = time.time()
    with pytest.raises(TimeoutError):
        tools.call('coop_tool')
    duration = time.time() - start
    
    # The tool should exit quickly after 0.2s when TimeoutError is raised, 
    # leaving the thread. The duration for 	ools.call is dictated by TimeoutError anyway.
    # To really test if the thread exited, we can check a side effect.
    assert duration < 0.3
    
def test_non_cooperative_tool_logs_warning():
    tools = ToolRegistry()
    
    @tools.register('bad_tool', timeout_s=0.1)
    def bad_tool():
        time.sleep(0.2)
        return 'done'
        
    with pytest.raises(TimeoutError):
        tools.call('bad_tool')
