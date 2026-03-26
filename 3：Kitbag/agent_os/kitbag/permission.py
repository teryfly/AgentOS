"""
High-risk tool permission checker.

Responsibilities:
- Enforce allowed_roles constraint for high-risk tools
- Empty allowed_roles → unrestricted (default for most tools)
- caller_role=None → allowed (system internal calls)

Design constraints:
- Raises ToolPermissionError on denial (caught by executor)
- Used only for high-risk tools (shell_run, python_exec)
- Not used for capability grouping (that's Actor.allowed_tools' job)
"""

from agent_os.common import ToolPermissionError
from .tool_base import Tool


class PermissionChecker:
    """
    Permission checker for tool execution.
    
    Enforces allowed_roles constraint as safety fallback for high-risk tools.
    Most tools should have empty allowed_roles (unrestricted).
    """

    def check(self, tool: Tool, caller_role: str | None) -> None:
        """
        Check if caller_role is allowed to use tool.
        
        Rules:
        1. allowed_roles empty → allow all (default for most tools)
        2. caller_role None → allow (system internal call)
        3. caller_role in allowed_roles → allow
        4. Otherwise → raise ToolPermissionError
        
        Args:
            tool: Tool instance to check
            caller_role: Role of the caller (from ToolCall.caller_role)
        
        Raises:
            ToolPermissionError: If caller_role not allowed
        
        Examples:
            >>> tool.allowed_roles = []
            >>> checker.check(tool, "programmer")  # OK (unrestricted)
            
            >>> tool.allowed_roles = ["coder", "programmer"]
            >>> checker.check(tool, "programmer")  # OK (in list)
            >>> checker.check(tool, "general")     # Raises ToolPermissionError
            
            >>> checker.check(tool, None)          # OK (system call)
        """
        # Rule 1: Empty allowed_roles = unrestricted
        if not tool.allowed_roles:
            return

        # Rule 2: System internal calls always allowed
        if caller_role is None:
            return

        # Rule 3: Check if caller_role in allowed list
        if caller_role in tool.allowed_roles:
            return

        # Rule 4: Deny access
        raise ToolPermissionError(
            f"Role '{caller_role}' not allowed to call tool '{tool.name}'. "
            f"Allowed roles: {tool.allowed_roles}"
        )