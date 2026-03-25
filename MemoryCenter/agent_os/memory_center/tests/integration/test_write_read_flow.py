"""
Integration tests for write-read flow.

Tests end-to-end persistence and retrieval of memories.
"""

import pytest

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestWriteReadFlow:
    """Integration tests for memory write and read operations."""

    async def test_write_single_and_read_back(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: A MemoryItem
        When: Writing and reading back
        Then: Retrieved item matches original
        """
        item = sample_memory_item(
            task_id="task-wr-001",
            type_=MemoryType.SHORT,
            content={"message": "test content"},
            metadata={"key": "value"},
        )

        await postgres_storage.save(item)

        results = await postgres_storage.query_by_task("task-wr-001")

        assert len(results) == 1
        assert results[0].id == item.id
        assert results[0].task_id == item.task_id
        assert results[0].type == item.type
        assert results[0].source == item.source
        assert results[0].content == item.content
        assert results[0].metadata == item.metadata

    async def test_write_batch_and_read_back(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple MemoryItems
        When: Batch writing and reading back
        Then: All items are correctly persisted
        """
        task_id = "task-wr-batch"
        items = [
            sample_memory_item(
                task_id=task_id,
                content={"index": i},
                created_at=1000 + i
            )
            for i in range(5)
        ]

        await postgres_storage.save_batch(items)

        results = await postgres_storage.query_by_task(task_id)

        assert len(results) == 5
        # Verify order (DESC by created_at)
        assert results[0].created_at == 1004
        assert results[4].created_at == 1000

    async def test_task_isolation(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories for multiple tasks
        When: Reading by specific task_id
        Then: Only memories for that task are returned
        """
        await postgres_storage.save_batch([
            sample_memory_item(task_id="task-a", content={"task": "a"}),
            sample_memory_item(task_id="task-a", content={"task": "a"}),
            sample_memory_item(task_id="task-b", content={"task": "b"}),
            sample_memory_item(task_id="task-c", content={"task": "c"}),
        ])

        results_a = await postgres_storage.query_by_task("task-a")
        results_b = await postgres_storage.query_by_task("task-b")
        results_c = await postgres_storage.query_by_task("task-c")

        assert len(results_a) == 2
        assert len(results_b) == 1
        assert len(results_c) == 1
        assert all(r.task_id == "task-a" for r in results_a)
        assert all(r.task_id == "task-b" for r in results_b)