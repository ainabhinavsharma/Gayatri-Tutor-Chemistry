
import logging
from core.agents.runtime import ToolRegistry, safe_log_args

def test_safe_log_args():
    kwargs = {
        'public_arg': 'hello',
        'api_key': 'secret123',
        'user_token': 'abc',
        'my_password_field': 'pass',
        'student_answer': 'I think the answer is 42',
        'content': 'Some long generated content',
        'message': 'Hello there'
    }
    
    safe = safe_log_args(kwargs)
    
    assert safe['public_arg'] == 'hello'
    assert safe['api_key'] == '[REDACTED]'
    assert safe['user_token'] == '[REDACTED]'
    assert safe['my_password_field'] == '[REDACTED]'
    assert safe['student_answer'] == '[REDACTED]'
    assert safe['content'] == '[REDACTED]'
    assert safe['message'] == '[REDACTED]'

def test_tool_registry_logs_safely(caplog):
    registry = ToolRegistry()
    
    def my_tool(public_arg: str, secret_token: str):
        return True
        
    registry.register('my_tool', argument_schema={'public_arg': str, 'secret_token': str})(my_tool)
    
    with caplog.at_level(logging.INFO):
        registry.call('my_tool', public_arg='visible', secret_token='hidden123')
        
    log_text = caplog.text
    assert 'Tool call: my_tool(args=[public_arg, secret_token])' in log_text
    assert 'visible' in log_text
    assert 'hidden123' not in log_text
    assert '[REDACTED]' in log_text
