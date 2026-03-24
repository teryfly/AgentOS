"""Integration tests for architect document parsing."""

import pytest
from coding_task_document_parser import CodingTaskDocumentParser, ParseResult


def test_parse_architect_document(sample_architect_document):
    """Parse complete architect document."""
    result = CodingTaskDocumentParser.parse(sample_architect_document)
    
    assert isinstance(result, ParseResult)
    assert result.estimate_n == 15
    assert result.source_type == "architect"
    assert result.sub_phases is None
    assert len(result.parse_warnings) == 0
    assert "End of the Coding Task Document" not in result.raw_document


def test_parse_estimate_count_architect(sample_architect_document):
    """Lightweight API returns correct integer."""
    count = CodingTaskDocumentParser.parse_estimate_count(sample_architect_document)
    assert count == 15
    assert isinstance(count, int)


def test_parse_architect_with_overflow(doc_overflow_estimate):
    """N > 1000 triggers overflow protection."""
    result = CodingTaskDocumentParser.parse(doc_overflow_estimate)
    
    assert result.estimate_n == 0
    assert len(result.parse_warnings) > 0
    assert any("exceeds 1000" in w for w in result.parse_warnings)


def test_parse_no_termination_line(doc_no_termination):
    """Missing termination line handled gracefully."""
    result = CodingTaskDocumentParser.parse(doc_no_termination)
    
    assert result.estimate_n == 0
    assert len(result.parse_warnings) > 0
    assert result.source_type == "architect"


def test_parse_multiple_termination_lines(doc_multiple_termination_lines):
    """Last termination line match is used."""
    result = CodingTaskDocumentParser.parse(doc_multiple_termination_lines)
    
    assert result.estimate_n == 20  # Last match value
    assert result.source_type == "architect"


def test_extract_from_group_architect(sample_group_final_content_architect):
    """Extract architect document from GroupActor content."""
    text = CodingTaskDocumentParser.extract_from_group_final_content(
        sample_group_final_content_architect
    )
    
    assert text != ""
    assert "# Coding Task Document" in text
    assert "estimate code file: 15" in text