"""
Subprocess protocol adapter and tool.

Responsibilities:
- Build SubprocessTool from YAML config
- Execute shell commands via subprocess.run
- Support timeout, cwd, capture_output

Design constraints:
- Shell execution is high-risk (requires allowed_roles)
- Stdout/stderr captured and returned in result
"""

import subprocess
import logging
from agent_os.common import ToolCategory, ParameterDef
from .base import ProtocolAdapter
from ..tool_base import Tool

logger = logging.getLogger(__name__)


class SubprocessProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for subprocess tools.
    
    Converts YAML subprocess protocol definitions into SubprocessTool instances.
    """

    def build_tools(self, tool_configs: list[dict], defaults: dict) -> list[Tool]:
        """
        Build SubprocessTool instances from YAML configuration.
        
        Args:
            tool_configs: List of per-tool configs
            defaults: Subprocess protocol defaults (unused currently)
        
        Returns:
            List of SubprocessTool instances
        """
        tools = []
        for config in tool_configs:
            try:
                tool = self._build_single_tool(config)
                tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to build subprocess tool '{config.get('name')}': {e}")
                raise
        return tools

    def _build_single_tool(self, config: dict) -> Tool:
        """
        Build single SubprocessTool from config.
        
        Args:
            config: Tool-specific config
        
        Returns:
            SubprocessTool instance
        """
        subprocess_config = config.get("subprocess", {})
        schema_params = self._build_parameters(config.get("parameters", {}))

        return SubprocessTool(
            name=config["name"],
            description=config["description"],
            category=ToolCategory(config["category"]),
            allowed_roles=config.get("allowed_roles", []),
            parameters=schema_params,
            subprocess_config=subprocess_config,
        )

    def _build_parameters(self, params_config: dict) -> dict[str, ParameterDef]:
        """
        Convert YAML parameters to ParameterDef dict.
        
        Args:
            params_config: Parameters from YAML
        
        Returns:
            Dict of parameter name to ParameterDef
        """
        result = {}
        for param_name, param_spec in params_config.items():
            result[param_name] = ParameterDef(
                type=param_spec["type"],
                required=param_spec["required"],
                description=param_spec["description"],
                default=param_spec.get("default"),
                enum=param_spec.get("enum"),
            )
        return result


class SubprocessTool(Tool):
    """
    Tool implementation for subprocess protocol.
    
    Executes shell commands via subprocess.run.
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        allowed_roles: list[str],
        parameters: dict[str, ParameterDef],
        subprocess_config: dict,
    ):
        """
        Initialize SubprocessTool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            allowed_roles: Allowed roles (typically non-empty for high-risk tools)
            parameters: Parameter definitions
            subprocess_config: Subprocess-specific config
        """
        super().__init__(name, description, category, allowed_roles, parameters)
        self._subprocess_config = subprocess_config

    def execute(self, params: dict) -> dict:
        """
        Execute shell command.
        
        Args:
            params: Validated parameters
        
        Returns:
            Dict with stdout, stderr, returncode
        
        Raises:
            TimeoutError: If command times out
            RuntimeError: If command execution fails
        """
        command_field = self._subprocess_config.get("command_field", "command")
        timeout_field = self._subprocess_config.get("timeout_field", "timeout")
        cwd_field = self._subprocess_config.get("cwd_field", "cwd")
        shell = self._subprocess_config.get("shell", True)
        capture_output = self._subprocess_config.get("capture_output", True)

        command = params[command_field]
        timeout = params.get(timeout_field, None)
        cwd = params.get(cwd_field, None)

        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"Command timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Command execution failed: {str(e)}")