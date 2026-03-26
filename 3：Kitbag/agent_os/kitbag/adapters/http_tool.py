"""
HttpTool implementation.

Responsibilities:
- Build HTTP request from config + params
- Substitute path parameters
- Map query/body parameters
- Inject Bearer authentication
- Execute via httpx

Design constraints:
- Uses httpx.Client for synchronous requests
- Timeout from config or default
"""

import os
import httpx
from typing import Any, Optional
from agent_os.common import ToolCategory, ParameterDef
from ..tool_base import Tool


class HttpTool(Tool):
    """
    Tool implementation for HTTP protocol.
    
    Executes HTTP requests using httpx library.
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        allowed_roles: list[str],
        parameters: dict[str, ParameterDef],
        http_config: dict,
        base_url: str,
        default_headers: dict,
        auth_config: Optional[dict],
    ):
        """
        Initialize HttpTool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            allowed_roles: Allowed roles
            parameters: Parameter definitions
            http_config: HTTP-specific config (method, path, etc.)
            base_url: Base URL from suite defaults
            default_headers: Default headers from suite defaults
            auth_config: Authentication config from suite defaults
        """
        super().__init__(name, description, category, allowed_roles, parameters)
        self._http_config = http_config
        self._base_url = base_url
        self._default_headers = default_headers or {}
        self._auth_config = auth_config

    def execute(self, params: dict) -> Any:
        """
        Execute HTTP request.
        
        Args:
            params: Validated parameters
        
        Returns:
            Response JSON or None if no content
        
        Raises:
            httpx.HTTPError: On HTTP errors
        """
        method = self._http_config["method"]
        path = self._http_config["path"]
        path_params = self._http_config.get("path_params", [])
        body_mapping = self._http_config.get("body_mapping", "all_params")
        query_mapping = self._http_config.get("query_mapping", "none")
        auth_required = self._http_config.get("auth_required", False)

        # Build URL with path param substitution
        url = self._build_url(path, params, path_params)

        # Build headers
        headers = self._build_headers(auth_required)

        # Map body and query
        body = self._map_body(params, path_params, body_mapping)
        query = self._map_query(params, path_params, query_mapping)

        # Execute request
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=query)
            elif method == "POST":
                response = client.post(url, headers=headers, json=body, params=query)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=body, params=query)
            elif method == "DELETE":
                response = client.delete(url, headers=headers, params=query)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json() if response.content else None

    def _build_url(self, path: str, params: dict, path_params: list) -> str:
        """
        Substitute {param} placeholders in path.
        
        Args:
            path: URL path template
            params: Request parameters
            path_params: List of path parameter names
        
        Returns:
            Complete URL with substitutions
        """
        url = self._base_url + path
        for param_name in path_params:
            placeholder = f"{{{param_name}}}"
            url = url.replace(placeholder, str(params[param_name]))
        return url

    def _build_headers(self, auth_required: bool) -> dict:
        """
        Merge default headers + auth if required.
        
        Args:
            auth_required: Whether to add authentication
        
        Returns:
            Headers dict
        """
        headers = dict(self._default_headers)
        if auth_required and self._auth_config:
            if self._auth_config["type"] == "bearer":
                token_env = self._auth_config["token_env"]
                token = os.environ.get(token_env)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
        return headers

    def _map_body(self, params: dict, path_params: list, mapping: str) -> dict:
        """
        Build request body based on mapping strategy.
        
        Args:
            params: Request parameters
            path_params: List of path parameter names
            mapping: Mapping strategy
        
        Returns:
            Request body dict
        """
        if mapping == "all_params":
            return params
        elif mapping == "exclude_path_params":
            return {k: v for k, v in params.items() if k not in path_params}
        else:
            return {}

    def _map_query(self, params: dict, path_params: list, mapping: str) -> dict:
        """
        Build query string based on mapping strategy.
        
        Args:
            params: Request parameters
            path_params: List of path parameter names
            mapping: Mapping strategy
        
        Returns:
            Query parameters dict
        """
        if mapping == "all_params":
            return params
        elif mapping == "exclude_path_params":
            return {k: v for k, v in params.items() if k not in path_params}
        else:
            return {}