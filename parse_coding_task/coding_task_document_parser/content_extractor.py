"""Content extraction from GroupActor FINAL content dict."""

import json
from . import history_collector


def extract_from_group_final_content(content: dict) -> str:
    """
    Priority-based extraction from GroupActor FINAL content dict.
    
    Priority order:
      1. final_output is dict with "sub_phases" → json.dumps()
      2. final_output is str with "Coding Task Document" → return as-is
      3. Fallback to history scanning → json.dumps() if found
      4. Final fallback → ""
    
    Args:
        content: GroupActor FINAL content dict with keys:
                 - history: list of turns
                 - final_output: str or dict
                 - shared_context: dict
                 - total_rounds: int
    
    Returns:
        Document text string (JSON or Markdown) or empty string
    """
    final_output = content.get("final_output")
    
    # Priority 1: Engineer JSON aggregation
    if isinstance(final_output, dict) and "sub_phases" in final_output:
        return json.dumps(final_output, ensure_ascii=False, indent=2)
    
    # Priority 2: Single document format (architect or engineer sub-phase)
    if isinstance(final_output, str) and "Coding Task Document" in final_output:
        return final_output
    
    # Priority 3: Fallback to history
    history = content.get("history", [])
    if history:
        sub_phases = history_collector.collect_sub_phases_from_history(history)
        if sub_phases:
            # Serialize to JSON aggregation format
            aggregated = {
                "sub_phases": [
                    {
                        "phase": sp.phase,
                        "title": sp.title,
                        "document": sp.document,
                        "estimate_n": sp.estimate_n
                    }
                    for sp in sub_phases
                ],
                "total_phases": len(sub_phases)
            }
            return json.dumps(aggregated, ensure_ascii=False, indent=2)
    
    # Priority 4: Final fallback
    return ""