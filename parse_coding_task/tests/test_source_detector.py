"""Tests for source_detector.py format classification."""

import pytest
from coding_task_document_parser import source_detector


def test_detect_json(sample_engineer_json):
    """Test detection of valid JSON with sub_phases."""
    source_type = source_detector.detect_source_type(sample_engineer_json)
    assert source_type == "json"


def test_detect_engineer_markdown(sample_engineer_sub_phase_doc):
    """Test detection of engineer phase heading."""
    source_type = source_detector.detect_source_type(sample_engineer_sub_phase_doc)
    assert source_type == "engineer"


def test_detect_architect(sample_architect_document):
    """Test detection of standard architect document."""
    source_type = source_detector.detect_source_type(sample_architect_document)
    assert source_type == "architect"


def test_detect_fallback():
    """Test fallback to architect for unknown format."""
    text = "Random text without any markers."
    source_type = source_detector.detect_source_type(text)
    assert source_type == "architect"


def test_invalid_json_not_detected():
    """Test malformed JSON not detected as json type."""
    text = '{"sub_phases": [invalid json}'
    source_type = source_detector.detect_source_type(text)
    assert source_type != "json"


def test_json_without_sub_phases_not_json_type():
    """Test JSON without sub_phases key not classified as json."""
    text = '{"other_key": "value"}'
    source_type = source_detector.detect_source_type(text)
    assert source_type == "architect"


def test_engineer_phase_priority_over_termination():
    """Test engineer phase marker takes priority over generic termination."""
    text = """# Coding Task Document - Phase 1.1 - Test

End of the Coding Task Document, the estimate code file: 10
"""
    source_type = source_detector.detect_source_type(text)
    assert source_type == "engineer"


def test_empty_text_fallback():
    """Test empty text falls back to architect."""
    source_type = source_detector.detect_source_type("")
    assert source_type == "architect"