"""
Unit tests for PostgreSQL storage delete operations.

Tests delete() and delete_by_task() methods.
"""

import pytest

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestPostgresStorageDelete:
    """Tests for delete operations in PostgresMemoryStorage."""

    async def test_delete_by_id(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: A persisted MemoryItem
        When: Deleting by memory_id
        Then: Item is removed from storage
        """
        item = sample_memory_item(task_id="task-del")
        await postgres_storage.save(item)

        await postgres_storage.delete(item.id)

        results = await postgres_storage.query_by_task("task-del")
        assert len(results) == 0

    async def test_delete_by_task_all_types(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple memories for a task
        When: Deleting by task_id without type filter
        Then: All memories for that task are removed
        """
        task_id = "task-del-all"
        items = [
            sample_memory_item(task_id=task_id, type_=MemoryType.SHORT),
            sample_memory_item(task_id=task_id, type_=MemoryType.LONG),
            sample_memory_item(task_id=task_id, type_=MemoryType.SHARED),
        ]
        await postgres_storage.save_batch(items)

        await postgres_storage.delete_by_task(task_id)

        results = await postgres_storage.query_by_task(task_id)
        assert len(results) == 0

    async def test_delete_by_task_with_type_filter(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple memories of different types
        When: Deleting with type filter
        Then: Only matching types are removed
        """
        task_id = "task-del-filter"
        items = [
            sample_memory_item(task_id=task_id, type_=MemoryType.SHORT),
            sample_memory_item(task_id=task_id, type_=MemoryType.SHORT),
            sample_memory_item(task_id=task_id, type_=MemoryType.LONG),
        ]
        await postgres_storage.save_batch(items)

        await postgres_storage.delete_by_task(
            task_id,
            types=[MemoryType.SHORT]
        )

        results = await postgres_storage.query_by_task(task_id)
        assert len(results) == 1
        assert results[0].type == MemoryType.LONG

    async def test_delete_nonexistent_id_no_error(
        self, postgres_storage
    ):
        """
        Given: A nonexistent memory_id
        When: Attempting to delete
        Then: Operation succeeds silently (no error)
        """
        await postgres_storage.delete("nonexistent-id")
        # No assertion needed - just verify no exception raised

    async def test_delete_isolates_tasks(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories for multiple tasks
        When: Deleting by task_id
        Then: Only memories for that task are removed
        """
        await postgres_storage.save_batch([
            sample_memory_item(task_id="task-keep"),
            sample_memory_item(task_id="task-keep"),
            sample_memory_item(task_id="task-delete"),
        ])

        await postgres_storage.delete_by_task("task-delete")

        kept = await postgres_storage.query_by_task("task-keep")
        deleted = await postgres_storage.query_by_task("task-delete")

        assert len(kept) == 2
        assert len(deleted) == 0