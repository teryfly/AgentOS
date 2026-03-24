"""Integration tests for edge cases and error handling."""

import pytest
from coding_task_document_parser import CodingTaskDocumentParser


def test_parse_empty_string():
    """Empty input handled gracefully."""
    result = CodingTaskDocumentParser.parse("")
    
    assert result.estimate_n == 0
    assert len(result.parse_warnings) > 0
    assert "Empty input" in result.parse_warnings[0]


def test_parse_none_input():
    """None input handled gracefully."""
    result = CodingTaskDocumentParser.parse(None)
    
    assert result.estimate_n == 0
    assert len(result.parse_warnings) > 0


def test_parse_whitespace_only():
    """Whitespace-only input treated as empty."""
    result = CodingTaskDocumentParser.parse("   \n\n   ")
    
    assert result.estimate_n == 0
    assert len(result.parse_warnings) > 0


def test_parse_invalid_json():
    """Invalid JSON handled gracefully."""
    result = CodingTaskDocumentParser.parse('{"sub_phases": [invalid}')
    
    assert result.estimate_n == 0
    assert len(result.parse_warnings) > 0


def test_parse_estimate_count_invalid():
    """Lightweight API returns 0 for invalid input."""
    count = CodingTaskDocumentParser.parse_estimate_count("invalid")
    assert count == 0


def test_extract_from_group_empty_content():
    """Empty content dict handled gracefully."""
    text = CodingTaskDocumentParser.extract_from_group_final_content({})
    assert text == ""


def test_extract_from_group_none():
    """None content handled gracefully."""
    text = CodingTaskDocumentParser.extract_from_group_final_content(None)
    assert text == ""


def test_collect_history_none():
    """None history handled gracefully."""
    sub_phases = CodingTaskDocumentParser.collect_sub_phases_from_history(None)
    assert sub_phases is None


def test_collect_history_invalid_structure():
    """Invalid history structure handled gracefully."""
    history = [
        "not a dict",
        {"missing": "actor_role"},
        {"actor_role": "engineer", "content": 12345}  # content not string
    ]
    sub_phases = CodingTaskDocumentParser.collect_sub_phases_from_history(history)
    assert sub_phases is None


def test_parse_no_exception_on_unexpected_error():
    """Catch-all ensures no exception propagation."""
    # Force an unusual scenario - parsing a very large nested structure
    complex_input = {"nested": {"data": "x" * 10000}}
    text = str(complex_input)
    
    result = CodingTaskDocumentParser.parse(text)
    
    # Should not raise, returns ParseResult with warnings
    assert isinstance(result.parse_warnings, list)


def test_parse_case_insensitive_termination():
    """Termination line matching is case-insensitive."""
    text = """# Document
END OF THE CODING TASK DOCUMENT, THE ESTIMATE CODE FILE: 25
"""
    result = CodingTaskDocumentParser.parse(text)
    assert result.estimate_n == 25


def test_parse_mixed_case_phase():
    """Phase extraction is case-insensitive."""
    text = """# Coding Task Document - PHASE 2.3 - Test
End of the Coding Task Document - Phase 2.3, the estimate code file: 15
"""
    result = CodingTaskDocumentParser.parse(text)
    assert result.source_type == "engineer"
    assert result.estimate_n == 15