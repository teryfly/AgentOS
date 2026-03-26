"""
HTTP protocol adapter.

Responsibilities:
- Merge http_defaults (base_url, headers, auth) with per-tool config
- Resolve environment variables in base_url and auth tokens
- Build HttpTool instances with request configuration

Design constraints:
- Supports path parameters, query parameters, body mapping
- Bearer token from env-var via token_env
"""

import logging
from agent_os.common import ToolCategory, ParameterDef
from .base import ProtocolAdapter
from .http_tool import HttpTool

logger = logging.getLogger(__name__)


class HttpProtocolAdapter(ProtocolAdapter):
    """
    Protocol adapter for HTTP tools.
    
    Converts YAML http protocol definitions into HttpTool instances.
    """

    def build_tools(self, tool_configs: list[dict], defaults: dict) -> list[HttpTool]:
        """
        Build HttpTool instances from YAML configuration.
        
        Args:
            tool_configs: List of per-tool configs
            defaults: HTTP protocol defaults (http_defaults)
        
        Returns:
            List of HttpTool instances
        """
        base_url = defaults.get("base_url", "")
        default_headers = defaults.get("headers", {})
        auth_config = defaults.get("auth")

        tools = []
        for config in tool_configs:
            try:
                tool = self._build_single_tool(config, base_url, default_headers, auth_config)
                tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to build HTTP tool '{config.get('name')}': {e}")
                raise
        return tools

    def _build_single_tool(
        self, config: dict, base_url: str, default_headers: dict, auth_config: dict
    ) -> HttpTool:
        """
        Build single HttpTool from config.
        
        Args:
            config: Tool-specific config
            base_url: Base URL from defaults
            default_headers: Default headers from defaults
            auth_config: Auth config from defaults
        
        Returns:
            HttpTool instance
        """
        http_config = config.get("http", {})
        schema_params = self._build_parameters(config.get("parameters", {}))

        return HttpTool(
            name=config["name"],
            description=config["description"],
            category=ToolCategory(config["category"]),
            allowed_roles=config.get("allowed_roles", []),
            parameters=schema_params,
            http_config=http_config,
            base_url=base_url,
            default_headers=default_headers,
            auth_config=auth_config,
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