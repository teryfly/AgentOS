"""
Unit tests for MemoryItem auto-generated ID functionality.

Tests acceptance criterion #39: MemoryItem.id auto-generation.
"""

import pytest

from agent_os.common import MemoryItem, MemorySource, MemoryType


class TestMemoryItemAutoId:
    """Tests for MemoryItem ID auto-generation."""

    def test_auto_generated_id_when_not_provided(self):
        """
        Given: MemoryItem created without id parameter
        When: Instance is created
        Then: ID is auto-generated as UUID
        
        Acceptance Criterion #39
        """
        item = MemoryItem(
            task_id="task-001",
            type=MemoryType.SHORT,
            source=MemorySource.ACTOR,
            content={"message": "test"},
        )

        assert item.id is not None
        assert isinstance(item.id, str)
        assert len(item.id) == 36  # UUID4 format

    def test_explicit_id_is_preserved(self):
        """
        Given: MemoryItem created with explicit id
        When: Instance is created
        Then: Provided ID is used
        
        Acceptance Criterion #40
        """
        custom_id = "custom-memory-id-123"
        
        item = MemoryItem(
            id=custom_id,
            task_id="task-001",
            type=MemoryType.SHORT,
            source=MemorySource.ACTOR,
            content={"message": "test"},
        )

        assert item.id == custom_id

    def test_multiple_items_have_unique_ids(self):
        """
        Given: Multiple MemoryItems created without IDs
        When: Instances are created
        Then: Each has a unique auto-generated ID
        """
        items = [
            MemoryItem(
                task_id="task-001",
                type=MemoryType.SHORT,
                source=MemorySource.ACTOR,
                content={"index": i},
            )
            for i in range(10)
        ]

        ids = [item.id for item in items]
        assert len(ids) == len(set(ids))  # All unique