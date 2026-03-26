"""
Unit tests for PermissionChecker edge cases.

Coverage:
- System internal calls (caller_role=None)
- Empty allowed_roles (unrestricted access)
- Multiple roles in allowed_roles
- Permission denied scenarios
- High-risk tool fallback behavior
"""

import pytest
from agent_os.common import ToolPermissionError
from agent_os.kitbag.permission import PermissionChecker
from tests.shared_mocks import MockTool, HighRiskMockTool


@pytest.fixture
def permission_checker():
    """Create permission checker instance."""
    return PermissionChecker()


def test_check_empty_allowed_roles_always_passes(permission_checker):
    """Test that tools with empty allowed_roles allow all callers."""
    tool = MockTool()
    assert tool.allowed_roles == []
    
    # Any role should be allowed
    permission_checker.check(tool, "user")
    permission_checker.check(tool, "admin")
    permission_checker.check(tool, "programmer")
    permission_checker.check(tool, "unknown_role")
    # No exceptions raised


def test_check_system_call_bypasses_all_restrictions(permission_checker):
    """Test that caller_role=None bypasses even high-risk tool restrictions."""
    tool = HighRiskMockTool()
    assert tool.allowed_roles == ["admin", "coder"]
    
    # System call should pass even for restricted tool
    permission_checker.check(tool, None)
    # No exception raised


def test_check_multiple_allowed_roles(permission_checker):
    """Test permission check with multiple roles in allowed_roles."""
    tool = HighRiskMockTool()
    assert "admin" in tool.allowed_roles
    assert "coder" in tool.allowed_roles
    
    # Both allowed roles should pass
    permission_checker.check(tool, "admin")
    permission_checker.check(tool, "coder")
    
    # Disallowed role should fail
    with pytest.raises(ToolPermissionError) as exc_info:
        permission_checker.check(tool, "user")
    assert "not allowed" in str(exc_info.value)
    assert "user" in str(exc_info.value)


def test_check_permission_error_message_format(permission_checker):
    """Test that ToolPermissionError contains helpful information."""
    tool = HighRiskMockTool()
    
    with pytest.raises(ToolPermissionError) as exc_info:
        permission_checker.check(tool, "unauthorized_user")
    
    error_msg = str(exc_info.value)
    assert "unauthorized_user" in error_msg
    assert tool.name in error_msg
    assert "admin" in error_msg
    assert "coder" in error_msg


def test_check_case_sensitive_role_matching(permission_checker):
    """Test that role matching is case-sensitive."""
    tool = HighRiskMockTool()
    
    # Exact match should pass
    permission_checker.check(tool, "admin")
    
    # Case mismatch should fail
    with pytest.raises(ToolPermissionError):
        permission_checker.check(tool, "Admin")
    
    with pytest.raises(ToolPermissionError):
        permission_checker.check(tool, "ADMIN")


def test_check_whitespace_role_not_trimmed(permission_checker):
    """Test that role names are not trimmed (exact match required)."""
    tool = HighRiskMockTool()
    
    # Role with whitespace should not match
    with pytest.raises(ToolPermissionError):
        permission_checker.check(tool, " admin")
    
    with pytest.raises(ToolPermissionError):
        permission_checker.check(tool, "admin ")