
import pytest
from typing import Literal
from pydantic import BaseModel, Field
from core.agents.runtime import ToolRegistry, FileToolInput
from core.config import TOOL_ARG_MAX_STRING_LENGTH

def test_pydantic_schema_rejects_out_of_range():
    tools = ToolRegistry()
    
    class RangeModel(BaseModel):
        count: int = Field(ge=1, le=10)
        
    @tools.register('range_tool', input_model=RangeModel)
    def range_tool(count: int):
        return count
        
    with pytest.raises(TypeError, match='Validation failed'):
        tools.call('range_tool', count=0)
        
    assert tools.call('range_tool', count=5) == 5

def test_pydantic_schema_rejects_wrong_literal():
    tools = ToolRegistry()
    
    class EnumModel(BaseModel):
        mode: Literal['read', 'write']
        
    @tools.register('enum_tool', input_model=EnumModel)
    def enum_tool(mode: str):
        return mode
        
    with pytest.raises(TypeError, match='Validation failed'):
        tools.call('enum_tool', mode='execute')
        
    assert tools.call('enum_tool', mode='read') == 'read'

def test_string_length_limit_enforced():
    tools = ToolRegistry()
    
    @tools.register('str_tool', argument_schema={'text': str})
    def str_tool(text: str):
        return text
        
    huge_str = 'a' * (TOOL_ARG_MAX_STRING_LENGTH + 1)
    
    with pytest.raises(TypeError, match='exceeds maximum string length'):
        tools.call('str_tool', text=huge_str)
        
    valid_str = 'a' * TOOL_ARG_MAX_STRING_LENGTH
    assert tools.call('str_tool', text=valid_str) == valid_str

def test_backward_compat_plain_type_dict():
    tools = ToolRegistry()
    
    @tools.register('old_tool', argument_schema={'age': int})
    def old_tool(age: int):
        return age
        
    with pytest.raises(TypeError, match='must be of type int'):
        tools.call('old_tool', age='twenty')
        
    assert tools.call('old_tool', age=20) == 20

def test_file_tool_input_guards_traversal():
    class TestFileModel(FileToolInput):
        file_path: str
        
    with pytest.raises(ValueError, match='Path traversal detected'):
        TestFileModel(file_path='../../windows/system32/cmd.exe')
        
    # Valid paths should work
    model = TestFileModel(file_path='valid_file.txt')
    assert model.file_path == 'valid_file.txt'
