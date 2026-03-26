"""
Orchestrates tool execution pipeline:
  lookup → permission → validate → execute → time → standardize → catch-all

Responsibilities:
- Coordinate between PermissionChecker, ParameterValidator, Tool, ResultStandardizer
- Measure elapsed time
- Capture all exceptions and convert to ToolResult(success=False)

Design constraints:
- All exceptions (ToolNotFoundError, ToolPermissionError, ToolValidationError, RuntimeError)
  are caught and converted to ToolResult
- No exception leakage to callers
- Elapsed time measured in milliseconds
"""

import time
import logging
from agent_os.common import ToolCall, ToolResult
from .tool_base import Tool
from .validator import ParameterValidator
from .permission import PermissionChecker
from .result_standardizer import ResultStandardizer

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool execution pipeline orchestrator.
    
    Coordinates the full execution flow from ToolCall to ToolResult.
    """

    def __init__(
        self,
        tools: dict,
        validator: ParameterValidator,
        permission_checker: PermissionChecker,
        result_standardizer: ResultStandardizer,
    ):
        """
        Initialize tool executor.
        
        Args:
            tools: Tool registry (name → {instance, schema})
            validator: Parameter validator
            permission_checker: Permission checker
            result_standardizer: Result standardizer
        """
        self._tools = tools
        self._validator = validator
        self._permission_checker = permission_checker
        self._result_standardizer = result_standardizer

    def execute(self, call: ToolCall) -> ToolResult:
        """
        Full execution pipeline. Returns ToolResult in all cases.
        
        Steps:
        1. Lookup tool (return error if not found)
        2. Permission check (high-risk tools only)
        3. Parameter validation
        4. Start timer
        5. Tool.execute()
        6. Stop timer
        7. Standardize result
        8. Catch all exceptions → ToolResult(success=False)
        
        Args:
            call: Tool call request
        
        Returns:
            ToolResult (never raises exceptions)
        
        Examples:
            >>> call = ToolCall(name="search", params={"query": "test"})
            >>> result = executor.execute(call)
            >>> result.success
            True
            
            >>> call = ToolCall(name="unknown_tool", params={})
            >>> result = executor.execute(call)
            >>> result.success
            False
            >>> "not found" in result.error
            True
        """
        try:
            # Step 1: Lookup
            entry = self._tools.get(call.name)
            if not entry:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Tool '{call.name}' not found",
                    tool_name=call.name,
                    elapsed_ms=0,
                )

            tool: Tool = entry["instance"]
            schema = entry["schema"]

            # Step 2: Permission check
            self._permission_checker.check(tool, call.caller_role)

            # Step 3: Validation
            validated_params = self._validator.validate(call.params, schema)

            # Step 4-6: Execute with timing
            start = time.perf_counter()
            result = tool.execute(validated_params)
            elapsed_ms = int((time.perf_counter() - start) * 1000)

            # Step 7: Standardize
            return self._result_standardizer.standardize(result, call.name, elapsed_ms)

        except Exception as e:
            # Step 8: Catch-all exception handling
            logger.error(f"Tool execution failed for '{call.name}': {e}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool_name=call.name,
                elapsed_ms=0,
            )