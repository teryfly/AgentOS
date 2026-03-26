"""
Unit tests for HTTP protocol adapter and tool.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from agent_os.kitbag.adapters.http_adapter import HttpProtocolAdapter


@pytest.fixture
def adapter():
    """Create HTTP protocol adapter."""
    return HttpProtocolAdapter()


def test_build_http_tool(adapter):
    """Test building HTTP tool."""
    defaults = {
        "base_url": "http://localhost:8000",
        "headers": {"Content-Type": "application/json"},
        "auth": {"type": "bearer", "token_env": "TEST_TOKEN"},
    }
    config = {
        "name": "test_http",
        "description": "Test HTTP tool",
        "category": "external",
        "allowed_roles": [],
        "parameters": {
            "id": {"type": "int", "required": True, "description": "ID"},
        },
        "http": {
            "method": "GET",
            "path": "/api/items/{id}",
            "path_params": ["id"],
        },
    }
    tools = adapter.build_tools([config], defaults)
    assert len(tools) == 1
    assert tools[0].name == "test_http"


@patch("httpx.Client")
def test_http_tool_get_request(mock_client_class, adapter):
    """Test HTTP GET request execution."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "success"}
    mock_response.content = b'{"result": "success"}'
    
    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_class.return_value = mock_client
    
    # Build tool
    defaults = {"base_url": "http://api.example.com"}
    config = {
        "name": "get_item",
        "description": "Get item",
        "category": "external",
        "allowed_roles": [],
        "parameters": {
            "id": {"type": "int", "required": True, "description": "ID"},
        },
        "http": {
            "method": "GET",
            "path": "/items/{id}",
            "path_params": ["id"],
        },
    }
    tools = adapter.build_tools([config], defaults)
    tool = tools[0]
    
    # Execute
    result = tool.execute({"id": 123})
    assert result == {"result": "success"}
    mock_client.get.assert_called_once()


@patch("httpx.Client")
def test_http_tool_post_request(mock_client_class, adapter):
    """Test HTTP POST request execution."""
    # Setup mock
    mock_response = MagicMock()
    mock_response.json.return_value = {"created": True}
    mock_response.content = b'{"created": true}'
    
    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__.return_value = mock_client
    mock_client_class.return_value = mock_client
    
    # Build tool
    defaults = {"base_url": "http://api.example.com"}
    config = {
        "name": "create_item",
        "description": "Create item",
        "category": "external",
        "allowed_roles": [],
        "parameters": {
            "name": {"type": "string", "required": True, "description": "Name"},
        },
        "http": {
            "method": "POST",
            "path": "/items",
            "body_mapping": "all_params",
        },
    }
    tools = adapter.build_tools([config], defaults)
    tool = tools[0]
    
    # Execute
    result = tool.execute({"name": "test"})
    assert result == {"created": True}


def test_http_tool_auth_injection(adapter):
    """Test that authentication header is injected."""
    os.environ["TEST_AUTH_TOKEN"] = "secret123"
    
    defaults = {
        "base_url": "http://api.example.com",
        "auth": {"type": "bearer", "token_env": "TEST_AUTH_TOKEN"},
    }
    config = {
        "name": "auth_tool",
        "description": "Auth tool",
        "category": "external",
        "allowed_roles": [],
        "parameters": {},
        "http": {
            "method": "GET",
            "path": "/secure",
            "auth_required": True,
        },
    }
    tools = adapter.build_tools([config], defaults)
    tool = tools[0]
    
    headers = tool._build_headers(auth_required=True)
    assert headers["Authorization"] == "Bearer secret123"