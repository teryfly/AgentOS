"""
Python protocol adapter.

Responsibilities:
- Dynamically import modules via importlib
- Instantiate classes with constructor_args
- Bind methods or module-level functions
- Build PythonTool instances with call_mode configuration

Design constraints:
- Merges python_defaults with per-tool python config
- Supports module.function and module.Class.method
- call_mode: direct/generator/async (async raises error in MVP)
"""

import importlib
import logging
from agent_os.common import ToolCategory, ParameterDef
from ..tool_base import Tool
from .base import ProtocolAdapter
from .python_tool import PythonTool

logger = logging.getLogger(__name__)


class PythonProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for Python tools.
    
    Converts YAML python protocol definitions into PythonTool instances.
    """

    def build_tools(self, tool_configs: list[dict], defaults: dict) -> list[Tool]:
        """
        Build PythonTool instances from YAML configuration.
        
        Args:
            tool_configs: List of per-tool configs
            defaults: Python protocol defaults (python_defaults)
        
        Returns:
            List of PythonTool instances
        """
        tools = []
        for config in tool_configs:
            try:
                tool = self._build_single_tool(config, defaults)
                tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to build Python tool '{config.get('name')}': {e}")
                raise
        return tools

    def _build_single_tool(self, config: dict, defaults: dict) -> PythonTool:
        """
        Build single PythonTool from config.
        
        Args:
            config: Tool-specific config
            defaults: Suite-level defaults
        
        Returns:
            PythonTool instance
        """
        # Merge defaults with tool-specific python config
        python_config = {**defaults, **config.get("python", {})}

        # Import module and resolve callable
        module_name = python_config["module"]
        class_name = python_config.get("class")
        method_name = python_config["method"]
        constructor_args = python_config.get("constructor_args", {})
        call_mode = python_config.get("call_mode", "direct")
        result_mapping = python_config.get("result_mapping")

        module = importlib.import_module(module_name)

        if class_name:
            # Class method
            cls = getattr(module, class_name)
            instance = cls(**constructor_args)
            callable_fn = getattr(instance, method_name)
        else:
            # Module-level function
            callable_fn = getattr(module, method_name)

        # Build parameter definitions
        schema_params = self._build_parameters(config.get("parameters", {}))

        return PythonTool(
            name=config["name"],
            description=config["description"],
            category=ToolCategory(config["category"]),
            allowed_roles=config.get("allowed_roles", []),
            parameters=schema_params,
            callable_fn=callable_fn,
            call_mode=call_mode,
            result_mapping=result_mapping,
            generator_runner=None,  # Injected by Kitbag during initialization
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