"""
Unit tests for Kitbag query interfaces.
"""

import pytest
from agent_os.common import ToolCategory
from agent_os.kitbag import Kitbag
from tests.shared_mocks import MockTool, HighRiskMockTool


def test_list_schemas_empty(kitbag):
    """Test list_schemas returns empty list for empty registry."""
    assert kitbag.list_schemas() == []


def test_list_schemas_returns_all(kitbag):
    """Test list_schemas returns all registered tools."""
    tool1 = MockTool(name="tool1")
    tool2 = MockTool(name="tool2")
    kitbag.register(tool1)
    kitbag.register(tool2)
    schemas = kitbag.list_schemas()
    assert len(schemas) == 2
    assert {s.name for s in schemas} == {"tool1", "tool2"}


def test_list_schemas_by_category(kitbag):
    """Test filtering schemas by category."""
    tool1 = MockTool(name="tool1")
    kitbag.register(tool1)
    data_schemas = kitbag.list_schemas_by_category(ToolCategory.DATA)
    assert len(data_schemas) == 1
    system_schemas = kitbag.list_schemas_by_category(ToolCategory.SYSTEM)
    assert len(system_schemas) == 0


def test_list_schemas_for_role_unrestricted(kitbag):
    """Test list_schemas_for_role with unrestricted tool."""
    tool = MockTool(name="tool1")
    kitbag.register(tool)
    schemas = kitbag.list_schemas_for_role("any_role")
    assert len(schemas) == 1


def test_list_schemas_for_role_restricted(kitbag):
    """Test list_schemas_for_role with role-restricted tool."""
    tool = HighRiskMockTool()
    kitbag.register(tool)
    
    # Allowed role
    schemas = kitbag.list_schemas_for_role("admin")
    assert len(schemas) == 1
    
    # Disallowed role
    schemas = kitbag.list_schemas_for_role("user")
    assert len(schemas) == 0


def test_get_schema_existing_tool(kitbag, mock_tool):
    """Test get_schema returns schema for existing tool."""
    kitbag.register(mock_tool)
    schema = kitbag.get_schema(mock_tool.name)
    assert schema is not None
    assert schema.name == mock_tool.name


def test_get_schema_nonexistent_tool(kitbag):
    """Test get_schema returns None for nonexistent tool."""
    schema = kitbag.get_schema("nonexistent")
    assert schema is None


def test_get_schema_returns_same_reference(kitbag, mock_tool):
    """Test get_schema returns same object reference on multiple calls."""
    kitbag.register(mock_tool)
    schema1 = kitbag.get_schema(mock_tool.name)
    schema2 = kitbag.get_schema(mock_tool.name)
    assert schema1 is schema2