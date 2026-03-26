"""
Central tool registry and execution facade.

Responsibilities:
- Maintain _tools registry: dict[str, {instance: Tool, schema: ToolSchema}]
- Provide registration/unregistration API
- Delegate execution to ToolExecutor
- Provide query interfaces for external modules (ActorRegistry, RegistrationCoordinator)

Design constraints:
- No direct dependency on TaskCenter, ActorRegistry, MemoryCenter
- All exceptions from execute() captured and converted to ToolResult
- Query methods (get_schema, exists) never raise exceptions
- Thread-safe for concurrent queries (no write locks in MVP)
"""

import logging
from dataclasses import dataclass
from typing import Optional
from agent_os.common import (
    ToolCall,
    ToolResult,
    ToolSchema,
    ToolCategory,
    DuplicateToolError,
    ToolNotFoundError,
)
from .tool_base import Tool
from .executor import ToolExecutor
from .validator import ParameterValidator
from .permission import PermissionChecker
from .result_standardizer import ResultStandardizer
from .generator_runner import GeneratorRunner

logger = logging.getLogger(__name__)


@dataclass
class KitbagConfig:
    """
    Kitbag configuration.
    
    Attributes:
        max_workers: ThreadPool size for generator-mode tools
        default_timeout_ms: Default tool timeout (0 = no timeout)
    """

    max_workers: int = 4
    default_timeout_ms: int = 0


class Kitbag:
    """
    Central tool registry and execution facade.
    
    Main entry point for tool registration, query, and execution.
    """

    def __init__(self, config: Optional[KitbagConfig] = None):
        """
        Initialize Kitbag.
        
        Args:
            config: Configuration (uses defaults if None)
        """
        self._tools: dict[str, dict] = {}  # name → {instance, schema}
        self._config = config or KitbagConfig()

        # Initialize dependencies
        self._validator = ParameterValidator()
        self._permission_checker = PermissionChecker()
        self._result_standardizer = ResultStandardizer()
        self._generator_runner = GeneratorRunner(max_workers=self._config.max_workers)
        self._executor = ToolExecutor(
            tools=self._tools,
            validator=self._validator,
            permission_checker=self._permission_checker,
            result_standardizer=self._result_standardizer,
        )

    def register(self, tool: Tool) -> None:
        """
        Register tool. Raises DuplicateToolError if name exists.
        
        Args:
            tool: Tool instance to register
        
        Raises:
            DuplicateToolError: If tool name already registered
        
        Examples:
            >>> kitbag.register(MyTool())
            >>> kitbag.register(MyTool())  # Raises DuplicateToolError
        """
        if tool.name in self._tools:
            raise DuplicateToolError(
                f"Tool '{tool.name}' is already registered. "
                f"Cannot register duplicate tools."
            )

        self._tools[tool.name] = {
            "instance": tool,
            "schema": tool.schema,
        }
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """
        Remove tool from registry. Raises ToolNotFoundError if not exists.
        
        Args:
            name: Tool name
        
        Raises:
            ToolNotFoundError: If tool not registered
        """
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not found in registry")

        del self._tools[name]
        logger.info(f"Unregistered tool: {name}")

    def exists(self, name: str) -> bool:
        """
        Check if tool is registered. Used by RegistrationCoordinator.
        
        Args:
            name: Tool name
        
        Returns:
            True if tool exists, False otherwise
        """
        return name in self._tools

    def execute(self, call: ToolCall) -> ToolResult:
        """
        Delegate to ToolExecutor. Never raises exceptions.
        
        Args:
            call: Tool call request
        
        Returns:
            ToolResult (success or failure)
        
        Examples:
            >>> result = kitbag.execute(ToolCall(name="search", params={"query": "test"}))
            >>> if result.success:
            ...     print(result.data)
        """
        return self._executor.execute(call)

    # Query interfaces (read-only, no side effects)

    def list_schemas(self) -> list[ToolSchema]:
        """
        List all tool schemas.
        
        Returns:
            List of all registered tool schemas
        """
        return [entry["schema"] for entry in self._tools.values()]

    def list_schemas_by_category(self, category: ToolCategory) -> list[ToolSchema]:
        """
        List tool schemas by category.
        
        Args:
            category: Tool category to filter by
        
        Returns:
            List of tool schemas in specified category
        """
        return [
            entry["schema"]
            for entry in self._tools.values()
            if entry["schema"].category == category
        ]

    def list_schemas_for_role(self, role: str) -> list[ToolSchema]:
        """
        List tool schemas available for specified role.
        
        Returns tools where:
        - allowed_roles is empty (unrestricted), OR
        - role is in allowed_roles
        
        Args:
            role: Role to check
        
        Returns:
            List of tool schemas accessible by role
        
        Note:
            Most tools have empty allowed_roles (unrestricted).
            AgentRuntime further filters by Actor.allowed_tools.
        """
        result = []
        for entry in self._tools.values():
            tool = entry["instance"]
            schema = entry["schema"]
            # Allow if empty allowed_roles or role in list
            if not tool.allowed_roles or role in tool.allowed_roles:
                result.append(schema)
        return result

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        """
        Get single tool schema by name.
        
        Used by ActorRegistry to build tool_capabilities.
        Never raises exceptions.
        
        Args:
            name: Tool name
        
        Returns:
            ToolSchema if exists, None otherwise
        
        Examples:
            >>> schema = kitbag.get_schema("search")
            >>> if schema:
            ...     print(schema.description)
        """
        entry = self._tools.get(name)
        return entry["schema"] if entry else None

    def get_generator_runner(self) -> GeneratorRunner:
        """
        Get generator runner instance for injection into PythonTool.
        
        Returns:
            GeneratorRunner instance
        """
        return self._generator_runner

    def shutdown(self):
        """Shutdown resources (e.g., generator runner thread pool)."""
        self._generator_runner.shutdown(wait=True)
        logger.info("Kitbag shutdown complete")