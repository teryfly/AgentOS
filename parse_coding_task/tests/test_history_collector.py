"""Tests for history_collector.py history scanning."""

import pytest
from coding_task_document_parser import history_collector


def test_collect_three_phases(sample_history_with_phases):
    """Test collecting 3 sub-phase documents from history."""
    sub_phases = history_collector.collect_sub_phases_from_history(sample_history_with_phases)
    
    assert sub_phases is not None
    assert len(sub_phases) == 2  # Fixture has 2 valid phases
    assert sub_phases[0].phase == "1.1"
    assert sub_phases[0].estimate_n == 8
    assert sub_phases[1].phase == "1.2"
    assert sub_phases[1].estimate_n == 12


def test_collect_skips_non_engineer():
    """Test non-engineer turns are skipped."""
    history = [
        {"actor_role": "user", "content": "# Coding Task Document - Phase 1.1\nEnd...file: 5"},
        {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.2 - Test\nEnd of the Coding Task Document - Phase 1.2, the estimate code file: 10"}
    ]
    sub_phases = history_collector.collect_sub_phases_from_history(history)
    
    assert len(sub_phases) == 1
    assert sub_phases[0].phase == "1.2"


def test_collect_skips_incomplete():
    """Test turns missing termination line are skipped."""
    history = [
        {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.1\nNo termination"},
        {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.2 - Test\nEnd of the Coding Task Document - Phase 1.2, the estimate code file: 10"}
    ]
    sub_phases = history_collector.collect_sub_phases_from_history(history)
    
    assert len(sub_phases) == 1
    assert sub_phases[0].phase == "1.2"


def test_collect_empty_history():
    """Test empty history returns None."""
    sub_phases = history_collector.collect_sub_phases_from_history([])
    assert sub_phases is None


def test_collect_no_matching(sample_history_no_phases):
    """Test history with no valid sub-phases returns None."""
    sub_phases = history_collector.collect_sub_phases_from_history(sample_history_no_phases)
    assert sub_phases is None


def test_extract_single_valid():
    """Test extracting SubPhase from valid content."""
    content = """# Coding Task Document - Phase 1.1 - Environment Setup

## Content
Test content here.

End of the Coding Task Document - Phase 1.1, the estimate code file: 8
"""
    sub_phase = history_collector._extract_sub_phase_from_content(content)
    
    assert sub_phase is not None
    assert sub_phase.phase == "1.1"
    assert sub_phase.title == "Environment Setup"
    assert sub_phase.estimate_n == 8


def test_extract_no_marker():
    """Test content without Phase marker returns None."""
    content = "Regular document without phase marker."
    sub_phase = history_collector._extract_sub_phase_from_content(content)
    assert sub_phase is None


def test_phase_ordering():
    """Test phases are collected in appearance order."""
    history = [
        {"actor_role": "engineer", "content": "# Coding Task Document - Phase 2.1 - Test\nEnd of the Coding Task Document - Phase 2.1, the estimate code file: 5"},
        {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.3 - Test\nEnd of the Coding Task Document - Phase 1.3, the estimate code file: 10"},
        {"actor_role": "engineer", "content": "# Coding Task Document - Phase 1.1 - Test\nEnd of the Coding Task Document - Phase 1.1, the estimate code file: 8"}
    ]
    sub_phases = history_collector.collect_sub_phases_from_history(history)
    
    assert len(sub_phases) == 3
    assert sub_phases[0].phase == "2.1"
    assert sub_phases[1].phase == "1.3"
    assert sub_phases[2].phase == "1.1"


def test_extract_title_optional():
    """Test title extraction handles missing title."""
    content = """# Coding Task Document - Phase 1.1

End of the Coding Task Document - Phase 1.1, the estimate code file: 8
"""
    sub_phase = history_collector._extract_sub_phase_from_content(content)
    
    assert sub_phase is not None
    assert sub_phase.title == ""