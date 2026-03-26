"""
Unit tests for environment variable substitution.
"""

import os
import pytest
from agent_os.kitbag.env_utils import substitute_env_vars


def test_substitute_simple_string():
    """Test simple string substitution."""
    os.environ["TEST_VAR"] = "value123"
    result = substitute_env_vars("prefix_${TEST_VAR}_suffix")
    assert result == "prefix_value123_suffix"


def test_substitute_multiple_vars():
    """Test multiple variable substitution."""
    os.environ["HOST"] = "localhost"
    os.environ["PORT"] = "8000"
    result = substitute_env_vars("http://${HOST}:${PORT}/api")
    assert result == "http://localhost:8000/api"


def test_substitute_missing_var():
    """Test that missing variables are preserved."""
    result = substitute_env_vars("${MISSING_VAR}")
    assert result == "${MISSING_VAR}"


def test_substitute_dict():
    """Test dictionary substitution."""
    os.environ["URL"] = "http://example.com"
    data = {"base_url": "${URL}", "timeout": 30}
    result = substitute_env_vars(data)
    assert result["base_url"] == "http://example.com"
    assert result["timeout"] == 30


def test_substitute_nested_dict():
    """Test nested dictionary substitution."""
    os.environ["TOKEN"] = "secret123"
    data = {"config": {"auth": {"token": "${TOKEN}"}}}
    result = substitute_env_vars(data)
    assert result["config"]["auth"]["token"] == "secret123"


def test_substitute_list():
    """Test list substitution."""
    os.environ["ITEM1"] = "value1"
    data = ["${ITEM1}", "static", "${MISSING}"]
    result = substitute_env_vars(data)
    assert result == ["value1", "static", "${MISSING}"]


def test_substitute_non_string_unchanged():
    """Test that non-string values are unchanged."""
    data = {"int": 42, "bool": True, "none": None}
    result = substitute_env_vars(data)
    assert result == data


def test_substitute_preserves_original():
    """Test that original data is not modified."""
    os.environ["VAR"] = "new"
    original = {"key": "${VAR}"}
    result = substitute_env_vars(original)
    assert original["key"] == "${VAR}"
    assert result["key"] == "new"