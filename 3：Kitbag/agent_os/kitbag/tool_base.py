"""
Tool abstract base class.

All concrete tools (PythonTool, HttpTool, SubprocessTool) inherit from this class.

Responsibilities:
- Define tool metadata (name, description, category, allowed_roles)
- Provide read-only schema property
- Declare abstract execute() method

Design constraints:
- Subclasses must implement execute()
- allowed_roles is empty list by default (unrestricted)
- schema is built from metadata and cached after first access
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from agent_os.common import ToolCategory, ToolSchema, ParameterDef


class Tool(ABC):
    """
    Abstract base class for all tools.
    
    Attributes:
        name: Globally unique tool identifier (snake_case)
        description: Natural language description for LLM understanding
        category: Tool category (system/data/ai/external/code)
        allowed_roles: Safety fallback - high-risk tools explicitly declare allowed roles
                      Empty list (default) = unrestricted (most tools)
                      Non-empty = only for high-risk tools (shell_run, python_exec)
        _parameters: Internal parameter definitions
        _schema_cache: Cached ToolSchema instance
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        allowed_roles: list[str],
        parameters: Dict[str, ParameterDef],
    ):
        """
        Initialize tool with metadata.
        
        Args:
            name: Tool name (globally unique)
            description: Tool description
            category: Tool category
            allowed_roles: Allowed roles (empty for unrestricted)
            parameters: Parameter definitions
        """
        self.name = name
        self.description = description
        self.category = category
        self.allowed_roles = allowed_roles if allowed_roles else []
        self._parameters = parameters
        self._schema_cache = None

    @property
    def schema(self) -> ToolSchema:
        """
        Build and cache ToolSchema from metadata.
        
        Returns:
            ToolSchema instance with tool metadata
        """
        if self._schema_cache is None:
            self._schema_cache = ToolSchema(
                name=self.name,
                description=self.description,
                category=self.category,
                parameters=self._parameters,
            )
        return self._schema_cache

    @abstractmethod
    def execute(self, params: dict) -> Any:
        """
        Execute tool with validated parameters.
        
        Args:
            params: Validated parameters (already checked by ParameterValidator)
        
        Returns:
            Tool execution result (protocol-specific type)
            - Can return ToolResult directly
            - Can return arbitrary type (will be standardized)
            - Can return None (will be wrapped in ToolResult)
        
        Raises:
            Any exception (will be caught by executor and converted to ToolResult)
        """
        raise NotImplementedError(f"Tool {self.name} must implement execute()")