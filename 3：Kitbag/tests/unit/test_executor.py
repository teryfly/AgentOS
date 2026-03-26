"""
Unit tests for ToolExecutor execution pipeline.
"""

import pytest
from agent_os.common import ToolCall, ToolPermissionError, ToolValidationError
from agent_os.kitbag import Kitbag
from tests.shared_mocks import MockTool, HighRiskMockTool


def test_execute_success(registered_kitbag, sample_tool_call):
    """Test successful tool execution."""
    result = registered_kitbag.execute(sample_tool_call)
    assert result.success
    assert result.tool_name == "mock_tool"
    assert result.elapsed_ms >= 0
    assert result.data == {"output": "success"}


def test_execute_tool_not_found(kitbag):
    """Test execution with nonexistent tool."""
    call = ToolCall(name="nonexistent", params={})
    result = kitbag.execute(call)
    assert not result.success
    assert "not found" in result.error


def test_execute_permission_denied(kitbag):
    """Test execution with permission denied."""
    tool = HighRiskMockTool()
    kitbag.register(tool)
    call = ToolCall(name="high_risk_tool", params={"command": "test"}, caller_role="user")
    result = kitbag.execute(call)
    assert not result.success
    assert "not allowed" in result.error


def test_execute_permission_granted(kitbag):
    """Test execution with permission granted."""
    tool = HighRiskMockTool()
    kitbag.register(tool)
    call = ToolCall(name="high_risk_tool", params={"command": "test"}, caller_role="admin")
    result = kitbag.execute(call)
    assert result.success


def test_execute_system_call_bypasses_permission(kitbag):
    """Test that caller_role=None bypasses permission check."""
    tool = HighRiskMockTool()
    kitbag.register(tool)
    call = ToolCall(name="high_risk_tool", params={"command": "test"}, caller_role=None)
    result = kitbag.execute(call)
    assert result.success


def test_execute_validation_error(kitbag, mock_tool):
    """Test execution with validation error."""
    kitbag.register(mock_tool)
    call = ToolCall(name="mock_tool", params={})  # Missing required param1
    result = kitbag.execute(call)
    assert not result.success
    assert "missing" in result.error.lower()


def test_execute_tool_exception(kitbag):
    """Test execution when tool raises exception."""
    tool = MockTool(name="failing_tool", fail=True)
    kitbag.register(tool)
    call = ToolCall(name="failing_tool", params={"param1": "test"})
    result = kitbag.execute(call)
    assert not result.success
    assert "failed" in result.error


def test_execute_measures_elapsed_time(registered_kitbag, sample_tool_call):
    """Test that elapsed_ms is measured."""
    result = registered_kitbag.execute(sample_tool_call)
    assert result.elapsed_ms >= 0
    assert isinstance(result.elapsed_ms, int)