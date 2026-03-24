"""JSON parsing for engineer aggregation format."""

import json
from .models import SubPhase


def parse_engineer_json(text: str) -> tuple[list[SubPhase], int, list[str]]:
    """
    Parse JSON string containing sub_phases array.
    
    Expected structure:
    {
      "sub_phases": [
        {"phase": "1.1", "title": "...", "document": "...", "estimate_n": 8},
        ...
      ],
      "total_phases": N
    }
    
    Args:
        text: JSON string
    
    Returns:
        Tuple of (sub_phases_list, total_estimate_n, warnings)
        - total_estimate_n = sum of all sub_phase estimate_n values
        - Invalid entries skipped with warnings
        - JSON decode error: ([], 0, [error_msg])
    """
    warnings = []
    
    # Try to parse JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return ([], 0, [f"JSON decode error: {str(e)}"])
    
    # Validate root structure
    if not isinstance(data, dict):
        return ([], 0, ["Root element must be a dict"])
    
    # Extract sub_phases array
    sub_phases_data = data.get("sub_phases", [])
    if not isinstance(sub_phases_data, list):
        return ([], 0, ["sub_phases must be an array"])
    
    # Process each entry
    sub_phases = []
    total_estimate = 0
    
    for idx, entry in enumerate(sub_phases_data):
        sub_phase, entry_warnings = _validate_sub_phase_entry(entry, idx)
        warnings.extend(entry_warnings)
        if sub_phase:
            sub_phases.append(sub_phase)
            total_estimate += sub_phase.estimate_n
    
    return (sub_phases, total_estimate, warnings)


def _validate_sub_phase_entry(entry: dict, index: int) -> tuple[SubPhase | None, list[str]]:
    """
    Validate a single sub_phase dict entry.
    
    Required fields: phase, title, document, estimate_n
    
    Args:
        entry: Dict entry from sub_phases array
        index: Array index for error reporting
    
    Returns:
        Tuple of (SubPhase instance or None, warnings list)
    """
    warnings = []
    
    # Check if entry is dict
    if not isinstance(entry, dict):
        return (None, [f"Entry {index} is not a dict"])
    
    # Check required fields
    required_fields = ["phase", "title", "document", "estimate_n"]
    missing = [f for f in required_fields if f not in entry]
    
    if missing:
        return (None, [f"Entry {index} missing fields: {missing}"])
    
    # Validate estimate_n type
    try:
        estimate_n = int(entry["estimate_n"])
    except (ValueError, TypeError):
        return (None, [f"Entry {index} has invalid estimate_n"])
    
    # Build SubPhase
    return (
        SubPhase(
            phase=str(entry["phase"]),
            title=str(entry["title"]),
            document=str(entry["document"]),
            estimate_n=estimate_n
        ),
        []
    )