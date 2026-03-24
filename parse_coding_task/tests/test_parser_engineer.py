"""Integration tests for engineer document parsing."""

import pytest
from coding_task_document_parser import CodingTaskDocumentParser


def test_parse_engineer_json(sample_engineer_json):
    """Parse engineer JSON aggregation format."""
    result = CodingTaskDocumentParser.parse(sample_engineer_json)
    
    assert result.source_type == "engineer"
    assert result.sub_phases is not None
    assert len(result.sub_phases) == 2
    assert result.estimate_n == 20  # 8 + 12
    assert result.sub_phases[0].phase == "1.1"
    assert result.sub_phases[1].phase == "1.2"


def test_parse_engineer_single_sub_phase(sample_engineer_sub_phase_doc):
    """Parse single engineer sub-phase document."""
    result = CodingTaskDocumentParser.parse(sample_engineer_sub_phase_doc)
    
    assert result.source_type == "engineer"
    assert result.sub_phases is None
    assert result.estimate_n == 8
    assert "End of the Coding Task Document" not in result.raw_document


def test_collect_sub_phases_from_history(sample_history_with_phases):
    """Collect sub-phases from history list."""
    sub_phases = CodingTaskDocumentParser.collect_sub_phases_from_history(
        sample_history_with_phases
    )
    
    assert sub_phases is not None
    assert len(sub_phases) == 2
    assert sub_phases[0].phase == "1.1"
    assert sub_phases[1].phase == "1.2"


def test_extract_and_parse_roundtrip(sample_group_final_content_engineer):
    """Test extraction and parsing roundtrip."""
    text = CodingTaskDocumentParser.extract_from_group_final_content(
        sample_group_final_content_engineer
    )
    
    result = CodingTaskDocumentParser.parse(text)
    
    assert result.source_type == "engineer"
    assert result.sub_phases is not None
    assert len(result.sub_phases) == 2


def test_parse_estimate_count_engineer_json(sample_engineer_json):
    """Lightweight API works with engineer JSON."""
    count = CodingTaskDocumentParser.parse_estimate_count(sample_engineer_json)
    assert count == 20  # Sum of sub-phase estimates


def test_parse_estimate_count_engineer_sub_phase(sample_engineer_sub_phase_doc):
    """Lightweight API works with single sub-phase."""
    count = CodingTaskDocumentParser.parse_estimate_count(sample_engineer_sub_phase_doc)
    assert count == 8


def test_collect_history_no_phases(sample_history_no_phases):
    """Collection returns None when no valid phases."""
    sub_phases = CodingTaskDocumentParser.collect_sub_phases_from_history(
        sample_history_no_phases
    )
    assert sub_phases is None