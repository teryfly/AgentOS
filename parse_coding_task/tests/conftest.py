"""Shared pytest fixtures for all tests."""

import pytest


@pytest.fixture
def sample_architect_document():
    """Valid architect Markdown with termination line."""
    return """# Coding Task Document

## Architecture Design
This is a detailed architecture section with multiple paragraphs.
It contains information about the system design and components.

## Modular Structure
File mappings and module descriptions go here.

End of the Coding Task Document, the estimate code file: 15
"""


@pytest.fixture
def sample_engineer_sub_phase_doc():
    """Valid engineer Phase 1.1 sub-phase document."""
    return """# Coding Task Document - Phase 1.1 - Environment Setup

## Objective
Setup project structure and dependencies.

## Implementation Steps
Step 1: Create directories
Step 2: Install dependencies

End of the Coding Task Document - Phase 1.1, the estimate code file: 8
"""


@pytest.fixture
def sample_engineer_json():
    """Valid engineer JSON aggregation string."""
    return """{
  "sub_phases": [
    {
      "phase": "1.1",
      "title": "Environment Setup",
      "document": "# Coding Task Document - Phase 1.1 - Environment Setup\\n...\\nEnd of the Coding Task Document - Phase 1.1, the estimate code file: 8",
      "estimate_n": 8
    },
    {
      "phase": "1.2",
      "title": "Core Implementation",
      "document": "# Coding Task Document - Phase 1.2 - Core Implementation\\n...\\nEnd of the Coding Task Document - Phase 1.2, the estimate code file: 12",
      "estimate_n": 12
    }
  ],
  "total_phases": 2
}"""


@pytest.fixture
def sample_engineer_json_dict():
    """Parsed dict version of engineer JSON."""
    return {
        "sub_phases": [
            {
                "phase": "1.1",
                "title": "Environment Setup",
                "document": "# Coding Task Document - Phase 1.1 - Environment Setup\n...\nEnd of the Coding Task Document - Phase 1.1, the estimate code file: 8",
                "estimate_n": 8
            },
            {
                "phase": "1.2",
                "title": "Core Implementation",
                "document": "# Coding Task Document - Phase 1.2 - Core Implementation\n...\nEnd of the Coding Task Document - Phase 1.2, the estimate code file: 12",
                "estimate_n": 12
            }
        ],
        "total_phases": 2
    }


@pytest.fixture
def sample_history_with_phases():
    """History list with 3 sub-phase documents."""
    return [
        {
            "round": 0,
            "actor_role": "engineer",
            "content": """# Coding Task Document - Phase 1.1 - Setup
Initial setup content here.
End of the Coding Task Document - Phase 1.1, the estimate code file: 8"""
        },
        {
            "round": 1,
            "actor_role": "engineer",
            "content": """# Coding Task Document - Phase 1.2 - Core
Core implementation content here.
End of the Coding Task Document - Phase 1.2, the estimate code file: 12"""
        },
        {
            "round": 2,
            "actor_role": "engineer",
            "content": "ALL_PHASES_COMPLETE"
        }
    ]


@pytest.fixture
def sample_history_no_phases():
    """History list with no valid sub-phase documents."""
    return [
        {"round": 0, "actor_role": "user", "content": "Start task"},
        {"round": 1, "actor_role": "engineer", "content": "Working on it..."}
    ]


@pytest.fixture
def sample_group_final_content_architect():
    """GroupActor FINAL content for architect output."""
    return {
        "history": [],
        "final_output": """# Coding Task Document

## Architecture Design
Content here.

End of the Coding Task Document, the estimate code file: 15""",
        "shared_context": {},
        "total_rounds": 1
    }


@pytest.fixture
def sample_group_final_content_engineer(sample_engineer_json_dict):
    """GroupActor FINAL content for engineer JSON aggregation."""
    return {
        "history": [],
        "final_output": sample_engineer_json_dict,
        "shared_context": {},
        "total_rounds": 3
    }


@pytest.fixture
def doc_no_termination():
    """Document missing termination line."""
    return """# Coding Task Document

## Architecture
This document has no termination line at all."""


@pytest.fixture
def doc_overflow_estimate():
    """Document with N > 1000."""
    return """# Coding Task Document

## Content
Some content here.

End of the Coding Task Document, the estimate code file: 1500
"""


@pytest.fixture
def doc_multiple_termination_lines():
    """Document with two termination lines."""
    return """# Coding Task Document

## Section 1
End of the Coding Task Document, the estimate code file: 10

## Section 2
More content here.

End of the Coding Task Document, the estimate code file: 20
"""