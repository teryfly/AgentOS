"""
Unit tests for Python protocol adapter and tool.
"""

import pytest
from agent_os.common import ToolCategory, ToolExecutionError
from agent_os.kitbag.adapters.python_adapter import PythonProtocolAdapter
from agent_os.kitbag.generator_runner import GeneratorRunner


def dummy_generator(**kwargs):
    """Dummy generator that accepts kwargs for testing."""
    for i in range(kwargs.get("stop", 3)):
        yield i


@pytest.fixture
def adapter():
    """Create Python protocol adapter."""
    return PythonProtocolAdapter()


def test_build_direct_mode_tool(adapter):
    """Test building direct mode Python tool."""
    config = {
        "name": "test_direct",
        "description": "Test direct tool",
        "category": "data",
        "allowed_roles": [],
        "parameters": {},
        "python": {
            "module": "os",
            "method": "getcwd",
            "call_mode": "direct",
        },
    }
    tools = adapter.build_tools([config], {})
    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "test_direct"
    
    # Execute tool
    result = tool.execute({})
    assert isinstance(result, str)  # cwd returns string


def test_build_class_method_tool(adapter):
    """Test building tool from class method."""
    config = {
        "name": "test_class",
        "description": "Test class tool",
        "category": "data",
        "allowed_roles": [],
        "parameters": {},
        "python": {
            "module": "pathlib",
            "class": "Path",
            "method": "cwd",
            "constructor_args": {},
            "call_mode": "direct",
        },
    }
    tools = adapter.build_tools([config], {})
    tool = tools[0]
    result = tool.execute({})
    assert result is not None


def test_generator_mode_requires_runner(adapter):
    """Test that generator mode tool requires GeneratorRunner."""
    config = {
        "name": "test_gen",
        "description": "Test generator",
        "category": "data",
        "allowed_roles": [],
        "parameters": {},
        "python": {
            "module": "tests.unit.test_python_protocol",
            "method": "dummy_generator",
            "call_mode": "generator",
            "result_mapping": {"strategy": "all"},
        },
    }
    tools = adapter.build_tools([config], {})
    tool = tools[0]
    
    # Should fail without generator runner
    with pytest.raises(RuntimeError) as exc_info:
        tool.execute({"stop": 5})
    assert "GeneratorRunner not injected" in str(exc_info.value)
    
    # Inject runner and test
    tool._generator_runner = GeneratorRunner(max_workers=1)
    result = tool.execute({"stop": 3})
    assert result == [0, 1, 2]


def test_async_mode_raises_error(adapter):
    """Test that async mode raises ToolExecutionError."""
    config = {
        "name": "test_async",
        "description": "Test async",
        "category": "data",
        "allowed_roles": [],
        "parameters": {},
        "python": {
            "module": "os",
            "method": "getcwd",
            "call_mode": "async",
        },
    }
    tools = adapter.build_tools([config], {})
    tool = tools[0]
    
    with pytest.raises(ToolExecutionError) as exc_info:
        tool.execute({})
    assert "not supported" in str(exc_info.value)


def test_build_with_defaults(adapter):
    """Test merging defaults with tool config."""
    defaults = {
        "module": "os.path",
        "call_mode": "direct",
    }
    config = {
        "name": "test_defaults",
        "description": "Test defaults",
        "category": "data",
        "allowed_roles": [],
        "parameters": {},
        "python": {
            "method": "exists",
        },
    }
    tools = adapter.build_tools([config], defaults)
    tool = tools[0]
    result = tool.execute({"path": "/tmp"})
    assert isinstance(result, bool)