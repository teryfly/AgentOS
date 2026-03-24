"""Tests for models.py data structures."""

import pytest
from coding_task_document_parser.models import ParseResult, SubPhase


def test_parse_result_instantiation():
    """Test ParseResult can be instantiated with valid data."""
    result = ParseResult(
        estimate_n=15,
        sub_phases=None,
        raw_document="Sample document",
        source_type="architect",
        parse_warnings=[]
    )
    
    assert result.estimate_n == 15
    assert result.sub_phases is None
    assert result.raw_document == "Sample document"
    assert result.source_type == "architect"
    assert result.parse_warnings == []


def test_sub_phase_instantiation():
    """Test SubPhase can be instantiated with valid data."""
    sub_phase = SubPhase(
        phase="1.1",
        title="Environment Setup",
        document="Full document text",
        estimate_n=8
    )
    
    assert sub_phase.phase == "1.1"
    assert sub_phase.title == "Environment Setup"
    assert sub_phase.document == "Full document text"
    assert sub_phase.estimate_n == 8


def test_parse_result_with_sub_phases():
    """Test ParseResult with populated sub_phases list."""
    sub_phases = [
        SubPhase("1.1", "Setup", "doc1", 8),
        SubPhase("1.2", "Core", "doc2", 12)
    ]
    
    result = ParseResult(
        estimate_n=20,
        sub_phases=sub_phases,
        raw_document="",
        source_type="engineer",
        parse_warnings=[]
    )
    
    assert len(result.sub_phases) == 2
    assert result.sub_phases[0].phase == "1.1"
    assert result.sub_phases[1].estimate_n == 12