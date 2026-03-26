"""
Unit tests for subprocess protocol adapter and tool.
"""

import pytest
from agent_os.kitbag.adapters.subprocess_adapter import SubprocessProtocolAdapter


@pytest.fixture
def adapter():
    """Create subprocess protocol adapter."""
    return SubprocessProtocolAdapter()


def test_build_subprocess_tool(adapter):
    """Test building subprocess tool."""
    config = {
        "name": "shell_test",
        "description": "Shell test",
        "category": "system",
        "allowed_roles": ["admin"],
        "parameters": {
            "command": {"type": "string", "required": True, "description": "Command"},
        },
        "subprocess": {
            "shell": True,
            "capture_output": True,
            "command_field": "command",
        },
    }
    tools = adapter.build_tools([config], {})
    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "shell_test"
    assert tool.allowed_roles == ["admin"]


def test_subprocess_tool_execution(adapter):
    """Test subprocess tool execution."""
    config = {
        "name": "echo_test",
        "description": "Echo test",
        "category": "system",
        "allowed_roles": [],
        "parameters": {
            "command": {"type": "string", "required": True, "description": "Command"},
        },
        "subprocess": {
            "shell": True,
            "capture_output": True,
            "command_field": "command",
        },
    }
    tools = adapter.build_tools([config], {})
    tool = tools[0]
    
    # Use python -c for cross-platform echo
    result = tool.execute({"command": 'python -c "print(\'hello\')"'})
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]


def test_subprocess_tool_timeout(adapter):
    """Test subprocess timeout handling."""
    config = {
        "name": "sleep_test",
        "description": "Sleep test",
        "category": "system",
        "allowed_roles": [],
        "parameters": {
            "command": {"type": "string", "required": True, "description": "Command"},
            "timeout": {"type": "int", "required": False, "default": 1, "description": "Timeout"},
        },
        "subprocess": {
            "shell": True,
            "capture_output": True,
            "command_field": "command",
            "timeout_field": "timeout",
        },
    }
    tools = adapter.build_tools([config], {})
    tool = tools[0]
    
    with pytest.raises(TimeoutError):
        # Use python -c for cross-platform sleep
        tool.execute({"command": 'python -c "import time; time.sleep(5)"', "timeout": 1})