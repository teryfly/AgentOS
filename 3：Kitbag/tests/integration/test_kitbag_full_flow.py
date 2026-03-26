"""
Integration tests for complete Kitbag workflow.
"""

import pytest
import tempfile
import os
from pathlib import Path
from agent_os.common import ToolCall
from agent_os.kitbag import Kitbag, YamlToolLoader


@pytest.fixture
def integration_env(tmp_path, monkeypatch):
    """Setup integration test environment with YAML files."""
    # Add tmp_path to sys.path so we can import the dummy module
    monkeypatch.syspath_prepend(str(tmp_path))
    
    # Create dummy module with generator function
    dummy_code = """
def dummy_range(**kwargs):
    for i in range(kwargs.get('stop', 5)):
        yield i
"""
    (tmp_path / "dummy_mod.py").write_text(dummy_code)
    
    # Create kitbags directory structure
    kitbags_dir = tmp_path / "kitbags"
    python_dir = kitbags_dir / "python"
    python_dir.mkdir(parents=True)
    
    # Create simple Python tool YAML
    python_tool_yaml = """
protocol: python
tools:
  - name: test_getcwd
    description: "Get current working directory"
    category: data
    allowed_roles: []
    parameters: {}
    python:
      module: "os"
      method: "getcwd"
      call_mode: direct
  - name: test_range
    description: "Generate range of numbers"
    category: data
    allowed_roles: []
    parameters:
      stop:
        type: int
        required: true
        description: "Stop value"
    python:
      module: "dummy_mod"
      method: "dummy_range"
      call_mode: generator
      result_mapping:
        strategy: all
"""
    (python_dir / "test_tools.yaml").write_text(python_tool_yaml)
    
    return kitbags_dir


def test_full_workflow_registration_and_execution(integration_env):
    """Test complete workflow: load YAML -> register -> query -> execute."""
    # Initialize Kitbag and loader
    kitbag = Kitbag()
    loader = YamlToolLoader()
    
    # Load tools from YAML
    loader.load_from_dir(kitbag, str(integration_env))
    
    # Verify registration
    assert kitbag.exists("test_getcwd")
    assert kitbag.exists("test_range")
    
    # Query tools
    schemas = kitbag.list_schemas()
    assert len(schemas) == 2
    
    schema = kitbag.get_schema("test_getcwd")
    assert schema is not None
    assert schema.name == "test_getcwd"
    
    # Execute direct mode tool
    call1 = ToolCall(name="test_getcwd", params={})
    result1 = kitbag.execute(call1)
    assert result1.success
    assert isinstance(result1.data, str)
    assert result1.elapsed_ms >= 0
    
    # Execute generator mode tool
    call2 = ToolCall(name="test_range", params={"stop": 5})
    result2 = kitbag.execute(call2)
    assert result2.success
    assert result2.data == [0, 1, 2, 3, 4]


def test_full_workflow_with_validation_error(integration_env):
    """Test workflow with parameter validation error."""
    kitbag = Kitbag()
    loader = YamlToolLoader()
    loader.load_from_dir(kitbag, str(integration_env))
    
    # Execute with missing required parameter
    call = ToolCall(name="test_range", params={})
    result = kitbag.execute(call)
    assert not result.success
    assert "missing" in result.error.lower()


def test_full_workflow_tool_not_found(integration_env):
    """Test workflow with nonexistent tool."""
    kitbag = Kitbag()
    loader = YamlToolLoader()
    loader.load_from_dir(kitbag, str(integration_env))
    
    call = ToolCall(name="nonexistent_tool", params={})
    result = kitbag.execute(call)
    assert not result.success
    assert "not found" in result.error


def test_full_workflow_list_schemas_for_role(integration_env):
    """Test querying schemas for specific role."""
    kitbag = Kitbag()
    loader = YamlToolLoader()
    loader.load_from_dir(kitbag, str(integration_env))
    
    # All test tools have empty allowed_roles, so all roles can access
    schemas = kitbag.list_schemas_for_role("any_role")
    assert len(schemas) == 2


def test_full_workflow_with_env_substitution(tmp_path):
    """Test workflow with environment variable substitution."""
    # Set environment variable
    os.environ["TEST_MODULE"] = "os"
    
    # Create YAML with env var
    kitbags_dir = tmp_path / "kitbags" / "python"
    kitbags_dir.mkdir(parents=True)
    
    yaml_content = """
protocol: python
tools:
  - name: env_test
    description: "Tool using env var"
    category: data
    allowed_roles: []
    parameters: {}
    python:
      module: "${TEST_MODULE}"
      method: "getpid"
      call_mode: direct
"""
    (kitbags_dir / "env_tool.yaml").write_text(yaml_content)
    
    # Load and execute
    kitbag = Kitbag()
    loader = YamlToolLoader()
    loader.load_from_dir(kitbag, str(tmp_path / "kitbags"))
    
    call = ToolCall(name="env_test", params={})
    result = kitbag.execute(call)
    assert result.success
    assert isinstance(result.data, int)  # getpid returns int


def test_full_workflow_shutdown(integration_env):
    """Test proper shutdown of Kitbag resources."""
    kitbag = Kitbag()
    loader = YamlToolLoader()
    loader.load_from_dir(kitbag, str(integration_env))
    
    # Execute some tools
    kitbag.execute(ToolCall(name="test_getcwd", params={}))
    kitbag.execute(ToolCall(name="test_range", params={"stop": 3}))
    
    # Shutdown
    kitbag.shutdown()
    # Verify no errors during shutdown