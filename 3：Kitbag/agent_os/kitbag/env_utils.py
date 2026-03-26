"""
Environment variable substitution for YAML configuration.

Responsibilities:
- Recursively walk dict/list/str structures
- Replace ${VAR} with os.environ.get(VAR)
- Preserve ${VAR} if VAR not in environment

Design constraints:
- Non-string values unchanged (int, bool, None)
- Partial substitution supported ("http://${HOST}:${PORT}")
- No validation of substituted values (YAML loader's responsibility)
"""

import os
import re
from typing import Any


def substitute_env_vars(data: Any) -> Any:
    """
    Recursively substitute ${VAR} with environment variables.
    
    Args:
        data: Configuration data (dict/list/str/int/bool/None)
    
    Returns:
        New structure with substitutions applied (original unchanged)
    
    Examples:
        >>> os.environ["HOST"] = "localhost"
        >>> substitute_env_vars("http://${HOST}:8000")
        'http://localhost:8000'
        
        >>> substitute_env_vars({"url": "${BASE_URL}/api"})
        {'url': 'http://example.com/api'}  # if BASE_URL is set
        
        >>> substitute_env_vars("${MISSING}")
        '${MISSING}'  # preserved if not in environment
    """
    if isinstance(data, dict):
        return {k: substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        return _substitute_in_string(data)
    else:
        # int, bool, None unchanged
        return data


def _substitute_in_string(text: str) -> str:
    """
    Replace all ${VAR} placeholders in string.
    
    Args:
        text: String potentially containing ${VAR} placeholders
    
    Returns:
        String with environment variables substituted
    """
    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        var_name = match.group(1)
        # Return env var value if exists, otherwise preserve placeholder
        return os.environ.get(var_name, match.group(0))

    return pattern.sub(replacer, text)