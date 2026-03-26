"""
Unit tests for ParameterValidator.
"""

import pytest
from agent_os.common import ToolSchema, ParameterDef, ToolCategory, ToolValidationError
from agent_os.kitbag.validator import ParameterValidator


@pytest.fixture
def validator():
    """Create validator instance."""
    return ParameterValidator()


@pytest.fixture
def schema():
    """Create test schema."""
    return ToolSchema(
        name="test_tool",
        description="Test tool",
        category=ToolCategory.DATA,
        parameters={
            "required_str": ParameterDef(
                type="string", required=True, description="Required string"
            ),
            "optional_int": ParameterDef(
                type="int", required=False, description="Optional int", default=10
            ),
            "enum_field": ParameterDef(
                type="string",
                required=True,
                description="Enum field",
                enum=["a", "b", "c"],
            ),
        },
    )


def test_validate_success(validator, schema):
    """Test successful validation."""
    params = {"required_str": "test", "enum_field": "a"}
    result = validator.validate(params, schema)
    assert result["required_str"] == "test"
    assert result["enum_field"] == "a"
    assert result["optional_int"] == 10  # Default filled


def test_validate_missing_required(validator, schema):
    """Test validation fails on missing required field."""
    params = {"enum_field": "a"}
    with pytest.raises(ToolValidationError) as exc_info:
        validator.validate(params, schema)
    assert "required_str" in str(exc_info.value)


def test_validate_enum_constraint(validator, schema):
    """Test enum constraint validation."""
    params = {"required_str": "test", "enum_field": "invalid"}
    with pytest.raises(ToolValidationError) as exc_info:
        validator.validate(params, schema)
    assert "enum" in str(exc_info.value)


def test_validate_type_coercion_str_to_int(validator):
    """Test type coercion from string to int."""
    schema = ToolSchema(
        name="test",
        description="Test",
        category=ToolCategory.DATA,
        parameters={
            "num": ParameterDef(type="int", required=True, description="Number")
        },
    )
    params = {"num": "42"}
    result = validator.validate(params, schema)
    assert result["num"] == 42
    assert isinstance(result["num"], int)


def test_validate_type_coercion_str_to_float(validator):
    """Test type coercion from string to float."""
    schema = ToolSchema(
        name="test",
        description="Test",
        category=ToolCategory.DATA,
        parameters={
            "num": ParameterDef(type="float", required=True, description="Number")
        },
    )
    params = {"num": "3.14"}
    result = validator.validate(params, schema)
    assert result["num"] == 3.14
    assert isinstance(result["num"], float)


def test_validate_type_coercion_int_to_float(validator):
    """Test type coercion from int to float."""
    schema = ToolSchema(
        name="test",
        description="Test",
        category=ToolCategory.DATA,
        parameters={
            "num": ParameterDef(type="float", required=True, description="Number")
        },
    )
    params = {"num": 42}
    result = validator.validate(params, schema)
    assert result["num"] == 42.0
    assert isinstance(result["num"], float)


def test_validate_type_mismatch(validator):
    """Test validation fails on type mismatch."""
    schema = ToolSchema(
        name="test",
        description="Test",
        category=ToolCategory.DATA,
        parameters={
            "num": ParameterDef(type="int", required=True, description="Number")
        },
    )
    params = {"num": "not_a_number"}
    with pytest.raises(ToolValidationError) as exc_info:
        validator.validate(params, schema)
    assert "expects" in str(exc_info.value)


def test_validate_preserves_unknown_fields(validator, schema, caplog):
    """Test that unknown fields are preserved with warning."""
    params = {"required_str": "test", "enum_field": "a", "unknown": "value"}
    result = validator.validate(params, schema)
    assert result["unknown"] == "value"
    assert "Unknown parameter" in caplog.text