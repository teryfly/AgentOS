"""History scanning to reconstruct sub-phase documents."""

import re
from .models import SubPhase
from . import termination


def collect_sub_phases_from_history(
    history: list[dict]
) -> list[SubPhase] | None:
    """
    Iterate history turns in order to extract engineer sub-phase documents.
    
    Processing rules:
      - Only process turns where actor_role == "engineer"
      - content must be string
      - Must contain "# Coding Task Document - Phase"
      - Must have valid termination line
    
    Args:
        history: List of conversation turn dicts
    
    Returns:
        List of SubPhase instances ordered by appearance, or None if no sub-phases found
    """
    sub_phases = []
    
    for turn in history:
        # Filter: only engineer turns
        if turn.get("actor_role") != "engineer":
            continue
        
        # Filter: content must be string
        content = turn.get("content", "")
        if not isinstance(content, str):
            continue
        
        # Attempt extraction
        sub_phase = _extract_sub_phase_from_content(content)
        if sub_phase:
            sub_phases.append(sub_phase)
    
    return sub_phases if sub_phases else None


def _extract_sub_phase_from_content(content: str) -> SubPhase | None:
    """
    Attempt to extract a single SubPhase from content string.
    
    Steps:
      1. Check for "# Coding Task Document - Phase" marker
      2. Find termination line matches
      3. Extract phase number from last match
      4. Extract estimate_n from last match
      5. Extract title from heading
      6. Return SubPhase
    
    Args:
        content: Turn content string
    
    Returns:
        SubPhase instance or None if format doesn't match
    """
    # Check for phase marker
    if "# Coding Task Document - Phase" not in content:
        return None
    
    # Find termination matches
    matches = termination.find_all_termination_matches(content)
    if not matches:
        return None
    
    last_match = matches[-1]
    
    # Extract phase number
    phase = termination.extract_phase_from_match(last_match)
    if not phase:
        return None
    
    # Extract estimate_n
    estimate_n, _ = termination.extract_estimate_from_match(last_match)
    
    # Extract title from heading
    title_match = re.search(
        r"# Coding Task Document - Phase \d+\.\d+\s*-\s*([^\n]+)",
        content,
        re.IGNORECASE
    )
    title = title_match.group(1).strip() if title_match else ""
    
    return SubPhase(
        phase=phase,
        title=title,
        document=content,
        estimate_n=estimate_n
    )