"""
Unit tests for Kitbag registration functionality.
"""

import pytest
from agent_os.common import DuplicateToolError, ToolNotFoundError
from agent_os.kitbag import Kitbag
from tests.shared_mocks import MockTool


def test_register_tool_success(kitbag, mock_tool):
    """Test successful tool registration."""
    kitbag.register(mock_tool)
    assert kitbag.exists(mock_tool.name)
    assert len(kitbag.list_schemas()) == 1


def test_register_duplicate_tool_raises_error(kitbag, mock_tool):
    """Test that registering duplicate tool raises DuplicateToolError."""
    kitbag.register(mock_tool)
    with pytest.raises(DuplicateToolError):
        kitbag.register(mock_tool)


def test_unregister_tool_success(kitbag, mock_tool):
    """Test successful tool unregistration."""
    kitbag.register(mock_tool)
    kitbag.unregister(mock_tool.name)
    assert not kitbag.exists(mock_tool.name)


def test_unregister_nonexistent_tool_raises_error(kitbag):
    """Test that unregistering nonexistent tool raises ToolNotFoundError."""
    with pytest.raises(ToolNotFoundError):
        kitbag.unregister("nonexistent_tool")


def test_exists_returns_correct_status(kitbag, mock_tool):
    """Test exists() returns correct boolean."""
    assert not kitbag.exists(mock_tool.name)
    kitbag.register(mock_tool)
    assert kitbag.exists(mock_tool.name)


def test_register_multiple_tools(kitbag):
    """Test registering multiple tools."""
    tool1 = MockTool(name="tool1")
    tool2 = MockTool(name="tool2")
    kitbag.register(tool1)
    kitbag.register(tool2)
    assert len(kitbag.list_schemas()) == 2
    assert kitbag.exists("tool1")
    assert kitbag.exists("tool2")