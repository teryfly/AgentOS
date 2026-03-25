"""
Unit tests for PostgreSQL storage write operations.

Tests save() and save_batch() methods with various scenarios.
"""

import pytest

from agent_os.common import MemorySource, MemoryType


@pytest.mark.asyncio
class TestPostgresStorageWrite:
    """Tests for write operations in PostgresMemoryStorage."""

    async def test_save_single_memory(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: A MemoryItem
        When: Saving to storage
        Then: Item is persisted and can be retrieved
        """
        item = sample_memory_item(task_id="task-001")

        await postgres_storage.save(item)

        # Verify by reading back
        results = await postgres_storage.query_by_task("task-001")
        assert len(results) == 1
        assert results[0].id == item.id
        assert results[0].content == item.content

    async def test_save_batch_multiple_memories(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple MemoryItems
        When: Batch saving to storage
        Then: All items are persisted
        """
        items = [
            sample_memory_item(task_id="task-batch", created_at=1000 + i)
            for i in range(5)
        ]

        await postgres_storage.save_batch(items)

        # Verify all saved
        results = await postgres_storage.query_by_task("task-batch")
        assert len(results) == 5

    async def test_auto_generated_id(self, postgres_storage, sample_memory_item):
        """
        Given: A MemoryItem without explicit id
        When: Saving to storage
        Then: ID is auto-generated
        """
        item = sample_memory_item(task_id="task-auto-id")

        # MemoryItem auto-generates UUID in __post_init__
        assert item.id is not None

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task("task-auto-id")
        assert len(results) == 1
        assert results[0].id == item.id

    async def test_save_with_metadata(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: A MemoryItem with metadata
        When: Saving to storage
        Then: Metadata is correctly persisted as JSONB
        """
        item = sample_memory_item(
            task_id="task-meta",
            source=MemorySource.TASK,
            metadata={"role": "architect", "has_coding_doc": True},
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task("task-meta")
        assert len(results) == 1
        assert results[0].metadata == {"role": "architect", "has_coding_doc": True}

    async def test_save_duplicate_id_raises_error(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: A MemoryItem with existing id
        When: Attempting to save again
        Then: Database raises unique constraint error
        """
        item = sample_memory_item(task_id="task-dup")

        await postgres_storage.save(item)

        # Attempt to save same item again
        with pytest.raises(Exception):  # asyncpg.UniqueViolationError
            await postgres_storage.save(item)