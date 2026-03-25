"""
Integration tests for context building.

Tests end-to-end context assembly with real storage.
"""

import pytest

from agent_os.common import MemoryType
from agent_os.memory_center import MemoryCenter


@pytest.mark.asyncio
class TestContextBuilding:
    """Integration tests for build_context functionality."""

    @pytest.fixture
    async def memory_center_instance(
        self, postgres_storage, memory_config, llm_gateway_config
    ):
        """Create MemoryCenter instance with real storage."""
        return MemoryCenter(
            storage=postgres_storage,
            config=memory_config,
            llm_gateway_config=llm_gateway_config,
        )

    async def test_build_context_with_all_sources(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: SHORT, SHARED, and searchable memories
        When: Building context with search query
        Then: All sources are included and properly ordered
        """
        task_id = "task-ctx-001"

        # Write test data
        await memory_center_instance.write_batch([
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                content={"message": "short memory with keyword"},
                created_at=3000
            ),
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHARED,
                content={"message": "shared context"},
                created_at=2000
            ),
        ])

        # Build context with search
        context = await memory_center_instance.build_context(
            task_id=task_id,
            include_shared=True,
            query="keyword"
        )

        # SHORT memory should be first (highest priority)
        assert len(context.items) >= 1
        assert context.items[0].type == MemoryType.SHORT

    async def test_build_context_respects_max_items(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: More memories than max_items_per_context
        When: Building context
        Then: Result is truncated and truncated flag is set
        """
        task_id = "task-ctx-truncate"
        memory_center_instance._config.max_items_per_context = 5

        # Write many memories
        await memory_center_instance.write_batch([
            sample_memory_item(task_id=task_id, created_at=1000 + i)
            for i in range(10)
        ])

        context = await memory_center_instance.build_context(task_id)

        assert len(context.items) == 5
        assert context.truncated is True

    async def test_build_context_without_shared(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: SHORT and SHARED memories
        When: Building context with include_shared=False
        Then: Only SHORT memories are included
        """
        task_id = "task-ctx-no-shared"

        await memory_center_instance.write_batch([
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                content={"type": "short"}
            ),
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHARED,
                content={"type": "shared"}
            ),
        ])

        context = await memory_center_instance.build_context(
            task_id,
            include_shared=False
        )

        assert all(item.type == MemoryType.SHORT for item in context.items)

    async def test_build_context_deduplication(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: Same memory appears in both direct query and search results
        When: Building context with search
        Then: Memory appears only once
        """
        task_id = "task-ctx-dedup"

        # Write a SHORT memory with searchable content
        item = sample_memory_item(
            task_id=task_id,
            type_=MemoryType.SHORT,
            content={"text": "unique searchable keyword"}
        )
        await memory_center_instance.write(item)

        # Build context with search that would match the same memory
        context = await memory_center_instance.build_context(
            task_id,
            include_shared=False,
            query="unique searchable keyword"
        )

        # Should have only one instance despite appearing in both SHORT and search
        memory_ids = [m.id for m in context.items]
        assert len(memory_ids) == len(set(memory_ids))  # All unique

    async def test_build_context_ordering(
        self, memory_center_instance, sample_memory_item
    ):
        """
        Given: Memories with different types and timestamps
        When: Building context
        Then: Results are properly ordered (type priority, then recency)
        """
        task_id = "task-ctx-order"

        await memory_center_instance.write_batch([
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                created_at=1000
            ),
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                created_at=2000
            ),
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHARED,
                created_at=3000
            ),
        ])

        context = await memory_center_instance.build_context(task_id)

        # First two should be SHORT (newest first)
        assert context.items[0].type == MemoryType.SHORT
        assert context.items[0].created_at == 2000
        assert context.items[1].type == MemoryType.SHORT
        assert context.items[1].created_at == 1000
        # Third should be SHARED
        assert context.items[2].type == MemoryType.SHARED

    async def test_build_context_empty_task(
        self, memory_center_instance
    ):
        """
        Given: No memories for a task
        When: Building context
        Then: Empty context is returned (not None)
        """
        context = await memory_center_instance.build_context("nonexistent-task")

        assert context.task_id == "nonexistent-task"
        assert context.items == []
        assert context.truncated is False