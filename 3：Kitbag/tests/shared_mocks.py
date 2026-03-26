"""
Shared mock classes for Kitbag tests.
"""

from agent_os.common import ToolCategory, ParameterDef
from agent_os.kitbag.tool_base import Tool


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name="mock_tool", fail=False, result=None):
        super().__init__(
            name=name,
            description="Mock tool for testing",
            category=ToolCategory.DATA,
            allowed_roles=[],
            parameters={
                "param1": ParameterDef(
                    type="string", required=True, description="Test parameter"
                ),
                "param2": ParameterDef(
                    type="int", required=False, description="Optional param", default=10
                ),
            },
        )
        self._fail = fail
        self._result = result if result is not None else {"output": "success"}

    def execute(self, params: dict):
        if self._fail:
            raise RuntimeError("Mock tool execution failed")
        return self._result


class HighRiskMockTool(Tool):
    """Mock high-risk tool with allowed_roles."""

    def __init__(self):
        super().__init__(
            name="high_risk_tool",
            description="High-risk mock tool",
            category=ToolCategory.SYSTEM,
            allowed_roles=["admin", "coder"],
            parameters={
                "command": ParameterDef(
                    type="string", required=True, description="Command to execute"
                )
            },
        )

    def execute(self, params: dict):
        return {"result": f"executed: {params['command']}"}