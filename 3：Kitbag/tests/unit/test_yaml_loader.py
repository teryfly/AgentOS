"""
Unit tests for YamlToolLoader.
"""

import pytest
import tempfile
import os
import logging
from pathlib import Path
from agent_os.kitbag import Kitbag, YamlToolLoader


@pytest.fixture
def temp_dir():
    """Create temporary directory for YAML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def loader():
    """Create YAML loader instance."""
    return YamlToolLoader()


def test_load_from_nonexistent_dir(kitbag, loader, caplog):
    """Test loading from nonexistent directory."""
    loader.load_from_dir(kitbag, "/nonexistent/path")
    assert "does not exist" in caplog.text


def test_load_skips_underscore_files(kitbag, loader, temp_dir, caplog):
    """Test that _*.yaml files are skipped."""
    caplog.set_level(logging.DEBUG)
    yaml_file = Path(temp_dir) / "_skip_me.yaml"
    yaml_file.write_text("protocol: python\ntools: []")
    
    loader.load_from_dir(kitbag, temp_dir)
    assert "Skipping file" in caplog.text


def test_load_python_tool(kitbag, loader, temp_dir):
    """Test loading Python tool from YAML."""
    yaml_content = """
protocol: python
tools:
  - name: test_tool
    description: "Test tool"
    category: data
    allowed_roles: []
    parameters:
      param1:
        type: string
        required: true
        description: "Test parameter"
    python:
      module: "os.path"
      method: "exists"
      call_mode: direct
"""
    yaml_file = Path(temp_dir) / "test.yaml"
    yaml_file.write_text(yaml_content)
    
    loader.load_from_dir(kitbag, temp_dir)
    assert kitbag.exists("test_tool")


def test_load_multi_document_yaml(kitbag, loader, temp_dir):
    """Test loading multi-document YAML file."""
    yaml_content = """
protocol: python
tools:
  - name: tool1
    description: "Tool 1"
    category: data
    allowed_roles: []
    parameters: {}
    python:
      module: "os"
      method: "getcwd"
      call_mode: direct
---
protocol: python
tools:
  - name: tool2
    description: "Tool 2"
    category: data
    allowed_roles: []
    parameters: {}
    python:
      module: "os"
      method: "getpid"
      call_mode: direct
"""
    yaml_file = Path(temp_dir) / "multi.yaml"
    yaml_file.write_text(yaml_content)
    
    loader.load_from_dir(kitbag, temp_dir)
    assert kitbag.exists("tool1")
    assert kitbag.exists("tool2")


def test_load_with_env_substitution(kitbag, loader, temp_dir):
    """Test environment variable substitution during loading."""
    os.environ["TEST_MODULE"] = "os.path"
    yaml_content = """
protocol: python
tools:
  - name: env_tool
    description: "Tool with env var"
    category: data
    allowed_roles: []
    parameters: {}
    python:
      module: "${TEST_MODULE}"
      method: "exists"
      call_mode: direct
"""
    yaml_file = Path(temp_dir) / "env.yaml"
    yaml_file.write_text(yaml_content)
    
    loader.load_from_dir(kitbag, temp_dir)
    assert kitbag.exists("env_tool")


def test_load_single_file_failure_isolation(kitbag, loader, temp_dir, caplog):
    """Test that single file failure doesn't stop loading others."""
    # Good file
    good_yaml = Path(temp_dir) / "good.yaml"
    good_yaml.write_text("""
protocol: python
tools:
  - name: good_tool
    description: "Good tool"
    category: data
    allowed_roles: []
    parameters: {}
    python:
      module: "os"
      method: "getcwd"
      call_mode: direct
""")
    
    # Bad file (missing protocol)
    bad_yaml = Path(temp_dir) / "bad.yaml"
    bad_yaml.write_text("""
tools:
  - name: bad_tool
""")
    
    loader.load_from_dir(kitbag, temp_dir)
    assert kitbag.exists("good_tool")
    assert not kitbag.exists("bad_tool")
    assert "Missing 'protocol'" in caplog.text