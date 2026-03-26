"""
Unit tests for HTTP protocol edge cases.

Coverage:
- Missing environment variables
- Empty response body
- HTTP error status codes
- Path parameter substitution edge cases
- Query/body mapping strategies
- Authentication header injection
- Timeout handling
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from agent_os.kitbag.adapters.http_adapter import HttpProtocolAdapter
from agent_os.kitbag.adapters.http_tool import HttpTool
from agent_os.common import ToolCategory, ParameterDef


@pytest.fixture
def adapter():
    """Create HTTP protocol adapter."""
    return HttpProtocolAdapter()


def test_http_tool_missing_env_var_for_auth():
    """Test HTTP tool behavior when auth token env var is missing."""
    # Ensure env var is not set
    if "MISSING_TOKEN" in os.environ:
        del os.environ["MISSING_TOKEN"]
    
    http_config = {
        "method": "GET",
        "path": "/secure",
        "auth_required": True,
    }
    
    tool = HttpTool(
        name="test_auth",
        description="Test auth",
        category=ToolCategory.EXTERNAL,
        allowed_roles=[],
        parameters={},
        http_config=http_config,
        base_url="http://example.com",
        default_headers={},
        auth_config={"type": "bearer", "token_env": "MISSING_TOKEN"},
    )
    
    # Should not crash, just omit Authorization header
    headers = tool._build_headers(auth_required=True)
    assert "Authorization" not in headers


@patch("httpx.Client")
def test_http_tool_empty_response_body(mock_client_class, adapter):
    """Test HTTP tool with empty response body."""
    mock_response = MagicMock()
    mock_response.json.return_value = None
    mock_response.content = b''  # Empty content
    
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_class.return_value = mock_client
    
    defaults = {"base_url": "http://api.example.com"}
    config = {
        "name": "get_empty",
        "description": "Get empty",
        "category": "external",
        "allowed_roles": [],
        "parameters": {},
        "http": {
            "method": "GET",
            "path": "/empty",
        },
    }
    
    tools = adapter.build_tools([config], defaults)
    tool = tools[0]
    
    result = tool.execute({})
    assert result is None  # Empty response returns None


@patch("httpx.Client")
def test_http_tool_http_error_status(mock_client_class, adapter):
    """Test HTTP tool with error status code."""
    import httpx
    
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found",
        request=MagicMock(),
        response=MagicMock()
    )
    
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_class.return_value = mock_client
    
    defaults = {"base_url": "http://api.example.com"}
    config = {
        "name": "get_404",
        "description": "Get 404",
        "category": "external",
        "allowed_roles": [],
        "parameters": {},
        "http": {
            "method": "GET",
            "path": "/notfound",
        },
    }
    
    tools = adapter.build_tools([config], defaults)
    tool = tools[0]
    
    with pytest.raises(httpx.HTTPStatusError):
        tool.execute({})


def test_http_tool_path_param_multiple_substitutions():
    """Test path parameter substitution with multiple params."""
    http_config = {
        "method": "GET",
        "path": "/users/{user_id}/posts/{post_id}",
        "path_params": ["user_id", "post_id"],
    }
    
    tool = HttpTool(
        name="test_multi_path",
        description="Test multiple path params",
        category=ToolCategory.EXTERNAL,
        allowed_roles=[],
        parameters={
            "user_id": ParameterDef(type="int", required=True, description="User ID"),
            "post_id": ParameterDef(type="int", required=True, description="Post ID"),
        },
        http_config=http_config,
        base_url="http://api.example.com",
        default_headers={},
        auth_config=None,
    )
    
    url = tool._build_url(
        "/users/{user_id}/posts/{post_id}",
        {"user_id": 123, "post_id": 456},
        ["user_id", "post_id"]
    )
    
    assert url == "http://api.example.com/users/123/posts/456"


def test_http_tool_body_mapping_all_params():
    """Test body mapping with all_params strategy."""
    http_config = {"method": "POST", "path": "/items", "body_mapping": "all_params"}
    
    tool = HttpTool(
        name="test_body_all",
        description="Test body all",
        category=ToolCategory.EXTERNAL,
        allowed_roles=[],
        parameters={},
        http_config=http_config,
        base_url="http://api.example.com",
        default_headers={},
        auth_config=None,
    )
    
    params = {"name": "test", "value": 42, "enabled": True}
    body = tool._map_body(params, [], "all_params")
    
    assert body == params


def test_http_tool_body_mapping_exclude_path_params():
    """Test body mapping with exclude_path_params strategy."""
    http_config = {
        "method": "POST",
        "path": "/items/{id}",
        "path_params": ["id"],
        "body_mapping": "exclude_path_params",
    }
    
    tool = HttpTool(
        name="test_body_exclude",
        description="Test body exclude",
        category=ToolCategory.EXTERNAL,
        allowed_roles=[],
        parameters={},
        http_config=http_config,
        base_url="http://api.example.com",
        default_headers={},
        auth_config=None,
    )
    
    params = {"id": 123, "name": "test", "value": 42}
    body = tool._map_body(params, ["id"], "exclude_path_params")
    
    assert body == {"name": "test", "value": 42}
    assert "id" not in body


def test_http_tool_query_mapping_all_params():
    """Test query mapping with all_params strategy."""
    http_config = {"method": "GET", "path": "/items", "query_mapping": "all_params"}
    
    tool = HttpTool(
        name="test_query_all",
        description="Test query all",
        category=ToolCategory.EXTERNAL,
        allowed_roles=[],
        parameters={},
        http_config=http_config,
        base_url="http://api.example.com",
        default_headers={},
        auth_config=None,
    )
    
    params = {"page": 1, "limit": 10, "sort": "name"}
    query = tool._map_query(params, [], "all_params")
    
    assert query == params


def test_http_tool_unsupported_method():
    """Test HTTP tool with unsupported HTTP method."""
    http_config = {"method": "PATCH", "path": "/items/1"}
    
    tool = HttpTool(
        name="test_patch",
        description="Test PATCH",
        category=ToolCategory.EXTERNAL,
        allowed_roles=[],
        parameters={},
        http_config=http_config,
        base_url="http://api.example.com",
        default_headers={},
        auth_config=None,
    )
    
    with pytest.raises(ValueError) as exc_info:
        with patch("httpx.Client"):
            tool.execute({})
    
    assert "Unsupported HTTP method" in str(exc_info.value)