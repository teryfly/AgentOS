"""Source format detection for Coding Task Documents."""

import json
import re
from typing import Literal
from . import termination


def detect_source_type(text: str) -> Literal["architect", "engineer", "json"]:
    """
    Classify input text format.
    
    Classification rules (priority order):
      1. Valid JSON with "sub_phases" key → "json"
      2. Contains "# Coding Task Document - Phase" (case-insensitive) → "engineer"
      3. Contains any termination line → "architect"
      4. Default fallback → "architect"
    
    Args:
        text: Document text to classify
    
    Returns:
        One of: "architect", "engineer", "json"
    """
    # Step 1: Try JSON parse
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "sub_phases" in data:
            return "json"
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Step 2: Check for engineer phase heading (case-insensitive)
    if re.search(r"#\s*Coding Task Document\s*-\s*Phase", text, re.IGNORECASE):
        return "engineer"
    
    # Step 3: Check for any termination line
    if termination.find_all_termination_matches(text):
        return "architect"
    
    # Step 4: Fallback
    return "architect"