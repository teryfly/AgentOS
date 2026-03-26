"""
Unit tests for ResultStandardizer.
"""

import pytest
from dataclasses import dataclass
from agent_os.common import ToolResult
from agent_os.kitbag.result_standardizer import ResultStandardizer


@pytest.fixture
def standardizer():
    """Create standardizer instance."""
    return ResultStandardizer()


@dataclass
class SampleDataclass:
    """Sample dataclass for testing."""

    value: int
    name: str


def test_standardize_tool_result_passthrough(standardizer):
    """Test that ToolResult is enriched and returned."""
    result = ToolResult(success=True, data={"key": "value"}, tool_name="old_tool", elapsed_ms=10)
    standardized = standardizer.standardize(result, "my_tool", 100)
    assert standardized is result
    assert standardized.tool_name == "my_tool"
    assert standardized.elapsed_ms == 100


def test_standardize_none(standardizer):
    """Test that None is wrapped in ToolResult."""
    result = standardizer.standardize(None, "my_tool", 50)
    assert result.success
    assert result.data is None
    assert result.tool_name == "my_tool"
    assert result.elapsed_ms == 50


def test_standardize_dataclass(standardizer):
    """Test that dataclass is converted to dict."""
    data = SampleDataclass(value=42, name="test")
    result = standardizer.standardize(data, "my_tool", 75)
    assert result.success
    assert result.data == {"value": 42, "name": "test"}
    assert result.tool_name == "my_tool"


def test_standardize_dataclass_conversion_failure(standardizer, monkeypatch, caplog):
    """Test fallback to str() on dataclass conversion failure."""
    
    @dataclass
    class BadDataclass:
        value: int
    
    # Mock asdict to raise exception
    import dataclasses
    original_asdict = dataclasses.asdict
    
    def mock_asdict(obj):
        raise ValueError("Conversion failed")
    
    monkeypatch.setattr(dataclasses, "asdict", mock_asdict)
    
    data = BadDataclass(value=42)
    result = standardizer.standardize(data, "my_tool", 60)
    
    assert result.success
    assert isinstance(result.data, str)
    assert "BadDataclass" in result.data
    assert "Failed to convert" in caplog.text


def test_standardize_arbitrary_type(standardizer):
    """Test that arbitrary types are wrapped in ToolResult."""
    data = {"key": "value", "nested": {"a": 1}}
    result = standardizer.standardize(data, "my_tool", 80)
    assert result.success
    assert result.data == data
    assert result.tool_name == "my_tool"