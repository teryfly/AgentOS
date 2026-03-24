"""Tests for json_parser.py JSON parsing."""

import pytest
from coding_task_document_parser import json_parser
from coding_task_document_parser.models import SubPhase


def test_parse_valid_json(sample_engineer_json):
    """Test parsing complete valid JSON."""
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(sample_engineer_json)
    
    assert len(sub_phases) == 2
    assert total_estimate == 20  # 8 + 12
    assert len(warnings) == 0
    
    assert sub_phases[0].phase == "1.1"
    assert sub_phases[0].estimate_n == 8
    assert sub_phases[1].phase == "1.2"
    assert sub_phases[1].estimate_n == 12


def test_parse_missing_fields():
    """Test entry missing required field gets skipped."""
    text = """{
  "sub_phases": [
    {"phase": "1.1", "document": "...", "estimate_n": 8},
    {"phase": "1.2", "title": "Core", "document": "...", "estimate_n": 12}
  ]
}"""
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(text)
    
    assert len(sub_phases) == 1
    assert sub_phases[0].phase == "1.2"
    assert total_estimate == 12
    assert len(warnings) == 1
    assert "missing fields" in warnings[0]


def test_parse_empty_array():
    """Test empty sub_phases array."""
    text = '{"sub_phases": []}'
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(text)
    
    assert len(sub_phases) == 0
    assert total_estimate == 0
    assert len(warnings) == 0


def test_parse_invalid_json():
    """Test malformed JSON string."""
    text = '{"sub_phases": [invalid json'
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(text)
    
    assert len(sub_phases) == 0
    assert total_estimate == 0
    assert len(warnings) == 1
    assert "JSON decode error" in warnings[0]


def test_parse_invalid_estimate_n():
    """Test entry with invalid estimate_n type."""
    text = """{
  "sub_phases": [
    {"phase": "1.1", "title": "Test", "document": "...", "estimate_n": "abc"}
  ]
}"""
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(text)
    
    assert len(sub_phases) == 0
    assert total_estimate == 0
    assert len(warnings) == 1
    assert "invalid estimate_n" in warnings[0]


def test_validate_entry_valid():
    """Test validation of valid dict entry."""
    entry = {
        "phase": "1.1",
        "title": "Test",
        "document": "Full doc",
        "estimate_n": 8
    }
    sub_phase, warnings = json_parser._validate_sub_phase_entry(entry, 0)
    
    assert isinstance(sub_phase, SubPhase)
    assert sub_phase.phase == "1.1"
    assert len(warnings) == 0


def test_validate_entry_not_dict():
    """Test validation rejects non-dict entry."""
    entry = "not a dict"
    sub_phase, warnings = json_parser._validate_sub_phase_entry(entry, 0)
    
    assert sub_phase is None
    assert len(warnings) == 1
    assert "not a dict" in warnings[0]


def test_parse_root_not_dict():
    """Test root element must be dict."""
    text = '["array", "not", "dict"]'
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(text)
    
    assert len(sub_phases) == 0
    assert total_estimate == 0
    assert "must be a dict" in warnings[0]


def test_parse_sub_phases_not_array():
    """Test sub_phases field must be array."""
    text = '{"sub_phases": "not an array"}'
    sub_phases, total_estimate, warnings = json_parser.parse_engineer_json(text)
    
    assert len(sub_phases) == 0
    assert total_estimate == 0
    assert "must be an array" in warnings[0]