"""
Unit tests for PostgreSQL storage read operations.

Tests query_by_task() with various filters and ordering.
"""

import pytest

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestPostgresStorageRead:
    """Tests for read operations in PostgresMemoryStorage."""

    async def test_query_by_task_returns_all_types(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple memories of different types for same task
        When: Querying by task_id without type filter
        Then: All memories are returned
        """
        task_id = "task-multi-type"
        items = [
            sample_memory_item(task_id=task_id, type_=MemoryType.SHORT),
            sample_memory_item(task_id=task_id, type_=MemoryType.LONG),
            sample_memory_item(task_id=task_id, type_=MemoryType.SHARED),
        ]

        await postgres_storage.save_batch(items)

        results = await postgres_storage.query_by_task(task_id)

        assert len(results) == 3
        types = {r.type for r in results}
        assert types == {MemoryType.SHORT, MemoryType.LONG, MemoryType.SHARED}

    async def test_query_by_task_with_type_filter(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple memories of different types
        When: Querying with type filter
        Then: Only matching types are returned
        """
        task_id = "task-filter"
        items = [
            sample_memory_item(task_id=task_id, type_=MemoryType.SHORT),
            sample_memory_item(task_id=task_id, type_=MemoryType.SHORT),
            sample_memory_item(task_id=task_id, type_=MemoryType.LONG),
        ]

        await postgres_storage.save_batch(items)

        results = await postgres_storage.query_by_task(
            task_id, types=[MemoryType.SHORT]
        )

        assert len(results) == 2
        assert all(r.type == MemoryType.SHORT for r in results)

    async def test_query_orders_by_created_at_desc(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple memories with different timestamps
        When: Querying by task_id
        Then: Results are ordered by created_at DESC (newest first)
        """
        task_id = "task-order"
        items = [
            sample_memory_item(task_id=task_id, created_at=1000),
            sample_memory_item(task_id=task_id, created_at=3000),
            sample_memory_item(task_id=task_id, created_at=2000),
        ]

        await postgres_storage.save_batch(items)

        results = await postgres_storage.query_by_task(task_id)

        assert len(results) == 3
        assert results[0].created_at == 3000
        assert results[1].created_at == 2000
        assert results[2].created_at == 1000

    async def test_query_empty_task_returns_empty_list(
        self, postgres_storage
    ):
        """
        Given: No memories for a task
        When: Querying by task_id
        Then: Empty list is returned
        """
        results = await postgres_storage.query_by_task("nonexistent-task")

        assert results == []

    async def test_query_isolates_tasks(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories for multiple tasks
        When: Querying by specific task_id
        Then: Only memories for that task are returned
        """
        await postgres_storage.save_batch([
            sample_memory_item(task_id="task-a"),
            sample_memory_item(task_id="task-a"),
            sample_memory_item(task_id="task-b"),
        ])

        results_a = await postgres_storage.query_by_task("task-a")
        results_b = await postgres_storage.query_by_task("task-b")

        assert len(results_a) == 2
        assert len(results_b) == 1
        assert all(r.task_id == "task-a" for r in results_a)
        assert all(r.task_id == "task-b" for r in results_b)