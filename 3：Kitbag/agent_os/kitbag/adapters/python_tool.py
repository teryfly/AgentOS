"""
PythonTool implementation.

Responsibilities:
- Execute Python callable in one of three modes: direct, generator, async
- Delegate generator execution to GeneratorRunner

Design constraints:
- Async mode raises ToolExecutionError in MVP
- Generator mode requires GeneratorRunner injection
"""

from typing import Any, Callable, Optional
from agent_os.common import ToolExecutionError, ToolCategory, ParameterDef
from ..tool_base import Tool
from ..generator_runner import GeneratorRunner


class PythonTool(Tool):
    """
    Tool implementation for Python protocol.
    
    Supports three call modes:
    - direct: Synchronous call, returns result directly
    - generator: Returns generator, consumed by GeneratorRunner
    - async: Async method (not supported in MVP)
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        allowed_roles: list[str],
        parameters: dict[str, ParameterDef],
        callable_fn: Callable,
        call_mode: str,
        result_mapping: Optional[dict],
        generator_runner: Optional[GeneratorRunner],
    ):
        """
        Initialize PythonTool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            allowed_roles: Allowed roles
            parameters: Parameter definitions
            callable_fn: Python callable to execute
            call_mode: Execution mode (direct/generator/async)
            result_mapping: Result mapping config (for generator mode)
            generator_runner: Generator runner (injected by Kitbag)
        """
        super().__init__(name, description, category, allowed_roles, parameters)
        self._callable_fn = callable_fn
        self._call_mode = call_mode
        self._result_mapping = result_mapping or {}
        self._generator_runner = generator_runner

    def execute(self, params: dict) -> Any:
        """
        Execute Python callable according to call_mode.
        
        Args:
            params: Validated parameters
        
        Returns:
            Execution result (type depends on call_mode)
        
        Raises:
            ToolExecutionError: If call_mode is invalid or async mode
            RuntimeError: If generator_runner not injected for generator mode
        """
        if self._call_mode == "direct":
            # Synchronous call
            return self._callable_fn(**params)

        elif self._call_mode == "generator":
            # Generator mode - run in thread pool
            if not self._generator_runner:
                raise RuntimeError(
                    f"GeneratorRunner not injected for tool '{self.name}'"
                )
            return self._generator_runner.run(
                self._callable_fn, params, self._result_mapping
            )

        elif self._call_mode == "async":
            # Async mode not supported in MVP
            raise ToolExecutionError(
                f"Async tools not supported in MVP. Tool '{self.name}' "
                f"cannot be executed."
            )

        else:
            raise ToolExecutionError(
                f"Unknown call_mode '{self._call_mode}' for tool '{self.name}'"
            )