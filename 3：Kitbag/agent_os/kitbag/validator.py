"""
Parameter validation engine.

Responsibilities:
- Check required fields presence
- Type checking with safe coercion (string→int/float, int→float)
- Enum constraint validation
- Default value filling for optional parameters
- Unknown field warnings (non-blocking)

Design constraints:
- Raises ToolValidationError on validation failure (caught by executor)
- Logs warnings for unknown fields but does not fail
- Type coercion follows safe rules only (no lossy conversions)
"""

import logging
from typing import Any, Dict
from agent_os.common import ToolSchema, ParameterDef, ToolValidationError

logger = logging.getLogger(__name__)

# Type mapping from string to Python type
TYPE_MAP = {
    "string": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,
    "list": list,
}


class ParameterValidator:
    """
    Parameter validation and normalization engine.
    
    Validates tool parameters against ToolSchema definition:
    - Required field checking
    - Type checking with safe coercion
    - Enum constraint validation
    - Default value filling
    - Unknown field warnings
    """

    def validate(self, params: dict, schema: ToolSchema) -> dict:
        """
        Validate and normalize parameters.
        
        Args:
            params: Raw parameters from ToolCall
            schema: Tool schema with parameter definitions
        
        Returns:
            Validated params dict with defaults filled
        
        Raises:
            ToolValidationError: On validation failure
        
        Examples:
            >>> params = {"query": "test", "top_k": "5"}
            >>> validated = validator.validate(params, schema)
            >>> validated["top_k"]  # Coerced to int
            5
            
            >>> params = {}  # Missing required field
            >>> validator.validate(params, schema)
            ToolValidationError: Required parameter 'query' missing
        """
        result = {}

        # Step 1: Check required fields, validate types, fill defaults
        for param_name, param_def in schema.parameters.items():
            if param_name not in params:
                # Missing parameter
                if param_def.required:
                    raise ToolValidationError(
                        f"Required parameter '{param_name}' missing for tool '{schema.name}'"
                    )
                elif param_def.default is not None:
                    # Fill default value
                    result[param_name] = param_def.default
                # Optional without default, skip
                continue

            value = params[param_name]

            # Type check with coercion
            value = self._check_and_coerce_type(value, param_def, param_name, schema.name)

            # Enum check
            if param_def.enum and value not in param_def.enum:
                raise ToolValidationError(
                    f"Parameter '{param_name}' value '{value}' not in enum {param_def.enum} "
                    f"for tool '{schema.name}'"
                )

            result[param_name] = value

        # Step 2: Warn on unknown fields (but preserve them)
        for param_name in params:
            if param_name not in schema.parameters:
                logger.warning(
                    f"Unknown parameter '{param_name}' provided to tool '{schema.name}'"
                )
                result[param_name] = params[param_name]  # Preserve unknown fields

        return result

    def _check_and_coerce_type(
        self, value: Any, param_def: ParameterDef, param_name: str, tool_name: str
    ) -> Any:
        """
        Check type and apply safe coercion.
        
        Safe coercions:
        - str → int (if parseable)
        - str → float (if parseable)
        - int → float (always safe)
        
        Args:
            value: Parameter value
            param_def: Parameter definition
            param_name: Parameter name (for error messages)
            tool_name: Tool name (for error messages)
        
        Returns:
            Coerced value
        
        Raises:
            ToolValidationError: If type mismatch and coercion fails
        """
        expected_type = TYPE_MAP.get(param_def.type)
        if expected_type is None:
            # Unknown type, pass through
            return value

        # Already correct type
        if isinstance(value, expected_type):
            return value

        # Coercion attempts
        try:
            if expected_type == int and isinstance(value, str):
                return int(value)
            if expected_type == float and isinstance(value, (str, int)):
                return float(value)
        except (ValueError, TypeError):
            pass

        # Type mismatch, no valid coercion
        raise ToolValidationError(
            f"Parameter '{param_name}' for tool '{tool_name}' expects {param_def.type}, "
            f"got {type(value).__name__}"
        )