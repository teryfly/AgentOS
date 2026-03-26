"""
Result standardization to ToolResult.

Responsibilities:
- Normalize any return value to ToolResult
- Handle special cases: ToolResult passthrough, None, dataclass→dict
- Enrich with tool_name and elapsed_ms

Design constraints:
- Never raises exceptions (fallback to str() if dataclass conversion fails)
- Dataclass conversion uses dataclasses.asdict()
- Preserves original ToolResult.success/error if already ToolResult
"""

import dataclasses
import logging
from typing import Any
from agent_os.common import ToolResult

logger = logging.getLogger(__name__)


class ResultStandardizer:
    """
    Result standardization to ToolResult.
    
    Converts arbitrary tool return values to standardized ToolResult format.
    """

    def standardize(self, result: Any, tool_name: str, elapsed_ms: int) -> ToolResult:
        """
        Normalize result to ToolResult.
        
        Cases:
        1. Already ToolResult → enrich tool_name + elapsed_ms
        2. None → ToolResult(success=True, data=None)
        3. Dataclass → asdict() then ToolResult(data=dict)
        4. Other → ToolResult(success=True, data=result)
        
        Args:
            result: Raw tool execution result
            tool_name: Tool name
            elapsed_ms: Execution time in milliseconds
        
        Returns:
            Standardized ToolResult
        
        Examples:
            >>> result = ToolResult(success=True, data={"key": "value"})
            >>> standardizer.standardize(result, "my_tool", 100)
            ToolResult(success=True, data={"key": "value"}, tool_name="my_tool", elapsed_ms=100)
            
            >>> result = None
            >>> standardizer.standardize(result, "my_tool", 50)
            ToolResult(success=True, data=None, tool_name="my_tool", elapsed_ms=50)
            
            >>> @dataclass
            >>> class MyResult:
            >>>     value: int
            >>> result = MyResult(value=42)
            >>> standardizer.standardize(result, "my_tool", 75)
            ToolResult(success=True, data={"value": 42}, tool_name="my_tool", elapsed_ms=75)
        """
        # Case 1: ToolResult passthrough
        if isinstance(result, ToolResult):
            result.tool_name = tool_name
            result.elapsed_ms = elapsed_ms
            return result

        # Case 2: None
        if result is None:
            return ToolResult(
                success=True,
                data=None,
                tool_name=tool_name,
                elapsed_ms=elapsed_ms,
            )

        # Case 3: Dataclass
        if dataclasses.is_dataclass(result) and not isinstance(result, type):
            try:
                data = dataclasses.asdict(result)
                return ToolResult(
                    success=True,
                    data=data,
                    tool_name=tool_name,
                    elapsed_ms=elapsed_ms,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to convert dataclass to dict for tool '{tool_name}': {e}. "
                    f"Falling back to str()."
                )
                return ToolResult(
                    success=True,
                    data=str(result),
                    tool_name=tool_name,
                    elapsed_ms=elapsed_ms,
                )

        # Case 4: Arbitrary type
        return ToolResult(
            success=True,
            data=result,
            tool_name=tool_name,
            elapsed_ms=elapsed_ms,
        )