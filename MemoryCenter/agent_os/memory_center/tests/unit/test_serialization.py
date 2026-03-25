"""
Unit tests for serialization helpers.

Tests bidirectional conversion between MemoryItem and database rows.
"""

import json
import uuid

import pytest

from agent_os.common import MemorySource, MemoryType
from agent_os.memory_center.storage.serialization import (
    batch_to_rows,
    memory_item_to_row,
    row_to_memory_item,
    rows_to_batch,
)


class TestMemoryItemToRow:
    """Tests for memory_item_to_row function."""

    def test_converts_basic_fields(self, sample_memory_item):
        """
        Given: A MemoryItem with basic fields
        When: Converting to row
        Then: All fields are correctly serialized
        """
        item = sample_memory_item(
            task_id="task-001",
            type_=MemoryType.SHORT,
            source=MemorySource.ACTOR,
        )

        row = memory_item_to_row(item)

        assert row["id"] == item.id
        assert row["task_id"] == item.task_id
        assert row["type"] == MemoryType.SHORT.value
        assert row["source"] == MemorySource.ACTOR.value
        assert row["created_at"] == item.created_at

    def test_serializes_content_to_json(self, sample_memory_item):
        """
        Given: A MemoryItem with complex content
        When: Converting to row
        Then: Content is JSON-serialized to string
        """
        item = sample_memory_item(
            content={"key": "value", "nested": {"data": 123}}
        )

        row = memory_item_to_row(item)

        assert isinstance(row["content"], str)
        parsed = json.loads(row["content"])
        assert parsed == {"key": "value", "nested": {"data": 123}}

    def test_preserves_metadata_as_dict(self, sample_memory_item):
        """
        Given: A MemoryItem with metadata
        When: Converting to row
        Then: Metadata is JSON-serialized to string for JSONB column
        """
        item = sample_memory_item(metadata={"role": "test", "flag": True})

        row = memory_item_to_row(item)

        # Metadata should be JSON string for PostgreSQL JSONB column
        assert isinstance(row["metadata"], str)
        parsed = json.loads(row["metadata"])
        assert parsed == {"role": "test", "flag": True}


class TestRowToMemoryItem:
    """Tests for row_to_memory_item function."""

    def test_converts_basic_fields(self):
        """
        Given: A database row with all fields
        When: Converting to MemoryItem
        Then: All fields are correctly deserialized
        """
        row = {
            "id": str(uuid.uuid4()),
            "task_id": "task-001",
            "type": MemoryType.SHORT.value,
            "source": MemorySource.ACTOR.value,
            "content": json.dumps({"message": "test"}),
            "metadata": json.dumps({"role": "test"}),
            "created_at": 1700000000000,
        }

        item = row_to_memory_item(row)

        assert item.id == row["id"]
        assert item.task_id == row["task_id"]
        assert item.type == MemoryType.SHORT
        assert item.source == MemorySource.ACTOR
        assert item.content == {"message": "test"}
        assert item.metadata == {"role": "test"}
        assert item.created_at == 1700000000000

    def test_deserializes_content_from_json(self):
        """
        Given: A row with JSON-serialized content
        When: Converting to MemoryItem
        Then: Content is correctly deserialized
        """
        row = {
            "id": str(uuid.uuid4()),
            "task_id": "task-001",
            "type": MemoryType.SHORT.value,
            "source": MemorySource.TOOL.value,
            "content": json.dumps({"tool": "exec", "result": [1, 2, 3]}),
            "metadata": json.dumps({}),
            "created_at": 1700000000000,
        }

        item = row_to_memory_item(row)

        assert item.content == {"tool": "exec", "result": [1, 2, 3]}


class TestBatchConversion:
    """Tests for batch conversion functions."""

    def test_batch_to_rows(self, sample_memory_item):
        """
        Given: A list of MemoryItem instances
        When: Converting to rows
        Then: All items are correctly serialized
        """
        items = [
            sample_memory_item(task_id="task-1"),
            sample_memory_item(task_id="task-2"),
            sample_memory_item(task_id="task-3"),
        ]

        rows = batch_to_rows(items)

        assert len(rows) == 3
        assert rows[0]["task_id"] == "task-1"
        assert rows[1]["task_id"] == "task-2"
        assert rows[2]["task_id"] == "task-3"

    def test_rows_to_batch(self):
        """
        Given: A list of database rows
        When: Converting to MemoryItem list
        Then: All rows are correctly deserialized
        """
        rows = [
            {
                "id": str(uuid.uuid4()),
                "task_id": f"task-{i}",
                "type": MemoryType.SHORT.value,
                "source": MemorySource.ACTOR.value,
                "content": json.dumps({"index": i}),
                "metadata": json.dumps({}),
                "created_at": 1700000000000 + i,
            }
            for i in range(3)
        ]

        items = rows_to_batch(rows)

        assert len(items) == 3
        assert items[0].task_id == "task-0"
        assert items[1].content == {"index": 1}
        assert items[2].created_at == 1700000000002