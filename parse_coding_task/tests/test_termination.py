"""Tests for termination.py regex operations."""

import pytest
from coding_task_document_parser import termination


def test_find_all_termination_matches_architect():
    """Test matching standard architect termination line."""
    text = "End of the Coding Task Document, the estimate code file: 15"
    matches = termination.find_all_termination_matches(text)
    assert len(matches) == 1


def test_find_all_termination_matches_engineer():
    """Test matching engineer phase termination line."""
    text = "End of the Coding Task Document - Phase 1.1, the estimate code file: 8"
    matches = termination.find_all_termination_matches(text)
    assert len(matches) == 1


def test_find_all_termination_matches_empty():
    """Test no matches for text without termination line."""
    text = "This is a document without termination line."
    matches = termination.find_all_termination_matches(text)
    assert len(matches) == 0


def test_extract_estimate_from_match_valid():
    """Test extracting valid estimate N."""
    text = "End of the Coding Task Document, the estimate code file: 15"
    matches = termination.find_all_termination_matches(text)
    estimate_n, warnings = termination.extract_estimate_from_match(matches[0])
    assert estimate_n == 15
    assert len(warnings) == 0


def test_extract_estimate_from_match_overflow():
    """Test overflow protection for N > 1000."""
    text = "End of the Coding Task Document, the estimate code file: 1500"
    matches = termination.find_all_termination_matches(text)
    estimate_n, warnings = termination.extract_estimate_from_match(matches[0])
    assert estimate_n == 0
    assert len(warnings) == 1
    assert "exceeds 1000" in warnings[0]


def test_extract_last_estimate_multiple():
    """Test last-match semantics with multiple termination lines."""
    text = """First section
End of the Coding Task Document, the estimate code file: 10
Second section
End of the Coding Task Document, the estimate code file: 20
"""
    estimate_n, warnings = termination.extract_last_estimate(text)
    assert estimate_n == 20
    assert len(warnings) == 0


def test_extract_last_estimate_no_termination():
    """Test handling of missing termination line."""
    text = "No termination line here."
    estimate_n, warnings = termination.extract_last_estimate(text)
    assert estimate_n == 0
    assert len(warnings) == 1
    assert "No termination line found" in warnings[0]


def test_extract_phase_from_match_engineer():
    """Test extracting phase number from engineer format."""
    text = "End of the Coding Task Document - Phase 1.1, the estimate code file: 8"
    matches = termination.find_all_termination_matches(text)
    phase = termination.extract_phase_from_match(matches[0])
    assert phase == "1.1"


def test_extract_phase_from_match_architect():
    """Test architect format returns None for phase."""
    text = "End of the Coding Task Document, the estimate code file: 15"
    matches = termination.find_all_termination_matches(text)
    phase = termination.extract_phase_from_match(matches[0])
    assert phase is None


def test_strip_termination_line():
    """Test removing last termination line."""
    text = """# Coding Task Document

## Content
Some content here.

End of the Coding Task Document, the estimate code file: 15
"""
    stripped = termination.strip_termination_line(text)
    assert "End of the Coding Task Document" not in stripped
    assert "# Coding Task Document" in stripped
    assert "Some content here." in stripped


def test_strip_termination_line_no_termination():
    """Test strip with no termination line returns original."""
    text = "No termination line."
    stripped = termination.strip_termination_line(text)
    assert stripped == text


def test_trailing_whitespace_handling():
    """Test extraction handles trailing whitespace."""
    text = "End of the Coding Task Document, the estimate code file: 15   \n\n"
    estimate_n, warnings = termination.extract_last_estimate(text)
    assert estimate_n == 15
    assert len(warnings) == 0


def test_is_engineer_phase_termination_true():
    """Test detection of engineer phase termination."""
    text = "End of the Coding Task Document - Phase 1.1, the estimate code file: 8"
    assert termination.is_engineer_phase_termination(text) is True


def test_is_engineer_phase_termination_false():
    """Test detection returns False for architect format."""
    text = "End of the Coding Task Document, the estimate code file: 15"
    assert termination.is_engineer_phase_termination(text) is False