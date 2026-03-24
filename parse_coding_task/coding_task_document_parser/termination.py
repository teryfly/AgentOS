"""Termination line regex operations for Coding Task Documents."""

import re


# Matches both architect and engineer termination formats
TERMINATION_PATTERN = re.compile(
    r"End of the Coding Task Document.*?the estimate code file:\s*(\d+)",
    re.IGNORECASE | re.MULTILINE
)

# Extract phase number from engineer format
PHASE_PATTERN = re.compile(
    r"End of the Coding Task Document\s*-\s*Phase\s+(\d+\.\d+)",
    re.IGNORECASE
)


def find_all_termination_matches(text: str) -> list[re.Match]:
    """
    Return all termination line matches in document order.
    
    Args:
        text: Document text to search
    
    Returns:
        List of regex match objects
    """
    return list(TERMINATION_PATTERN.finditer(text))


def extract_estimate_from_match(match: re.Match) -> tuple[int, list[str]]:
    """
    Extract N from a single regex match.
    
    Args:
        match: Regex match object from TERMINATION_PATTERN
    
    Returns:
        Tuple of (estimate_n, warnings)
        - If N > 1000: (0, [overflow_warning])
        - If conversion fails: (0, [format_warning])
        - Otherwise: (N, [])
    """
    warnings = []
    
    try:
        # Extract and clean the captured group
        n_str = match.group(1).strip()
        estimate_n = int(n_str)
        
        # Overflow protection
        if estimate_n > 1000:
            warnings.append("Estimate N exceeds 1000, treated as parse error")
            return (0, warnings)
        
        return (estimate_n, warnings)
    
    except (ValueError, AttributeError):
        warnings.append("Invalid estimate format in termination line")
        return (0, warnings)


def extract_last_estimate(text: str) -> tuple[int, list[str]]:
    """
    Find all termination matches, extract N from last one.
    
    Args:
        text: Document text to search
    
    Returns:
        Tuple of (estimate_n, warnings)
        - No matches: (0, [no_termination_warning])
    """
    matches = find_all_termination_matches(text)
    
    if not matches:
        return (0, ["No termination line found"])
    
    # Use last match (last-match semantics)
    return extract_estimate_from_match(matches[-1])


def extract_phase_from_match(match: re.Match) -> str | None:
    """
    Extract phase string 'X.Y' from match using PHASE_PATTERN.
    
    Args:
        match: Regex match object from TERMINATION_PATTERN
    
    Returns:
        Phase string like "1.1", or None for architect format
    """
    # Get the full matched text
    matched_text = match.group(0)
    
    # Try to find phase number
    phase_match = PHASE_PATTERN.search(matched_text)
    if phase_match:
        return phase_match.group(1)
    
    return None


def strip_termination_line(text: str) -> str:
    """
    Remove the last termination line from text.
    
    Args:
        text: Document text
    
    Returns:
        Text with last termination line removed
    """
    matches = find_all_termination_matches(text)
    
    if not matches:
        return text
    
    # Get last match
    last_match = matches[-1]
    
    # Split at the start of the last match and take everything before
    return text[:last_match.start()].rstrip()


def is_engineer_phase_termination(text: str) -> bool:
    """
    Check if text contains engineer Phase-specific termination.
    
    Args:
        text: Document text to check
    
    Returns:
        True if contains Phase termination format
    """
    matches = find_all_termination_matches(text)
    
    for match in matches:
        if extract_phase_from_match(match) is not None:
            return True
    
    return False