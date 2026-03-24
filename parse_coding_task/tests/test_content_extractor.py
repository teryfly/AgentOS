"""Tests for content_extractor.py content extraction."""

import json
import pytest
from coding_task_document_parser import content_extractor


def test_extract_json_final_output(sample_group_final_content_engineer):
    """Test extraction when final_output is dict with sub_phases."""
    text = content_extractor.extract_from_group_final_content(sample_group_final_content_engineer)
    
    assert text != ""
    data = json.loads(text)
    assert "sub_phases" in data
    assert len(data["sub_phases"]) == 2


def test_extract_markdown_final_output(sample_group_final_content_architect):
    """Test extraction when final_output is str with marker."""
    text = content_extractor.extract_from_group_final_content(sample_group_final_content_architect)
    
    assert text != ""
    assert "# Coding Task Document" in text
    assert "End of the Coding Task Document" in text


def test_fallback_to_history():
    """Test fallback to history when final_output invalid."""
    content = {
        "history": [
            {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.1 - Test\nEnd of the Coding Task Document - Phase 1.1, the estimate code file: 8"}
        ],
        "final_output": "invalid output",
        "shared_context": {},
        "total_rounds": 1
    }
    text = content_extractor.extract_from_group_final_content(content)
    
    assert text != ""
    data = json.loads(text)
    assert "sub_phases" in data
    assert len(data["sub_phases"]) == 1


def test_final_fallback_empty():
    """Test final fallback returns empty string."""
    content = {
        "history": [],
        "final_output": "no markers here",
        "shared_context": {},
        "total_rounds": 0
    }
    text = content_extractor.extract_from_group_final_content(content)
    assert text == ""


def test_missing_final_output_key():
    """Test handling of missing final_output key."""
    content = {
        "history": [
            {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.1 - Test\nEnd of the Coding Task Document - Phase 1.1, the estimate code file: 8"}
        ],
        "shared_context": {},
        "total_rounds": 1
    }
    text = content_extractor.extract_from_group_final_content(content)
    
    assert text != ""
    data = json.loads(text)
    assert len(data["sub_phases"]) == 1


def test_history_produces_json():
    """Test history with 2 sub-phases produces valid JSON."""
    content = {
        "history": [
            {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.1 - Setup\nEnd of the Coding Task Document - Phase 1.1, the estimate code file: 8"},
            {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.2 - Core\nEnd of the Coding Task Document - Phase 1.2, the estimate code file: 12"}
        ],
        "final_output": {},
        "shared_context": {},
        "total_rounds": 2
    }
    text = content_extractor.extract_from_group_final_content(content)
    
    data = json.loads(text)
    assert len(data["sub_phases"]) == 2
    assert data["total_phases"] == 2
    assert data["sub_phases"][0]["phase"] == "1.1"
    assert data["sub_phases"][1]["estimate_n"] == 12


def test_priority_order_json_over_markdown():
    """Test JSON final_output takes priority over string."""
    content = {
        "history": [],
        "final_output": {
            "sub_phases": [
                {"phase": "1.1", "title": "Test", "document": "...", "estimate_n": 5}
            ]
        },
        "shared_context": {},
        "total_rounds": 1
    }
    text = content_extractor.extract_from_group_final_content(content)
    
    data = json.loads(text)
    assert "sub_phases" in data