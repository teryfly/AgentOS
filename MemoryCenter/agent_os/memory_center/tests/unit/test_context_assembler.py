"""
Unit tests for context assembly algorithm.

Tests the pure logic of context building: deduplication, sorting, truncation.
"""

from unittest.mock import AsyncMock

import pytest

from agent_os.common import MemoryType
from agent_os.memory_center.context_assembler import (
    _deduplicate_memories,
    _priority_sort,
    _truncate,
    assemble_context,
)


class TestDeduplication:
    """Tests for _deduplicate_memories function."""

    def test_removes_duplicates_across_sources(self, sample_memory_item):
        """
        Given: Same memory_id appears in SHORT, SHARED, and search results
        When: Deduplicating
        Then: Only one instance is kept (from SHORT, highest priority)
        """
        duplicate_id = "mem-123"

        short_item = sample_memory_item(task_id="t1")
        short_item.id = duplicate_id

        shared_item = sample_memory_item(task_id="t1", type_=MemoryType.SHARED)
        shared_item.id = duplicate_id

        search_item = sample_memory_item(task_id="t1", type_=MemoryType.LONG)
        search_item.id = duplicate_id

        result = _deduplicate_memories([short_item], [shared_item], [search_item])

        assert len(result) == 1
        assert result[0].type == MemoryType.SHORT

    def test_preserves_unique_items(self, sample_memory_item):
        """
        Given: Unique items across all sources
        When: Deduplicating
        Then: All items are retained
        """
        short = [sample_memory_item(created_at=1000)]
        shared = [sample_memory_item(type_=MemoryType.SHARED, created_at=2000)]
        search = [sample_memory_item(type_=MemoryType.LONG, created_at=3000)]

        result = _deduplicate_memories(short, shared, search)

        assert len(result) == 3


class TestPrioritySort:
    """Tests for _priority_sort function."""

    def test_sorts_by_type_priority(self, sample_memory_item):
        """
        Given: Mixed memory types
        When: Sorting
        Then: SHORT < SHARED < LONG order
        """
        items = [
            sample_memory_item(type_=MemoryType.LONG, created_at=1000),
            sample_memory_item(type_=MemoryType.SHORT, created_at=1000),
            sample_memory_item(type_=MemoryType.SHARED, created_at=1000),
        ]

        result = _priority_sort(items)

        assert result[0].type == MemoryType.SHORT
        assert result[1].type == MemoryType.SHARED
        assert result[2].type == MemoryType.LONG

    def test_sorts_by_recency_within_type(self, sample_memory_item):
        """
        Given: Multiple items of same type with different timestamps
        When: Sorting
        Then: Newest first (created_at DESC) within each type
        """
        items = [
            sample_memory_item(type_=MemoryType.SHORT, created_at=1000),
            sample_memory_item(type_=MemoryType.SHORT, created_at=3000),
            sample_memory_item(type_=MemoryType.SHORT, created_at=2000),
        ]

        result = _priority_sort(items)

        assert result[0].created_at == 3000
        assert result[1].created_at == 2000
        assert result[2].created_at == 1000


class TestTruncation:
    """Tests for _truncate function."""

    def test_truncates_when_exceeding_limit(self, sample_memory_item):
        """
        Given: More items than max_items
        When: Truncating
        Then: Only first max_items are kept, truncated flag is True
        """
        items = [sample_memory_item(created_at=i) for i in range(10)]

        result, was_truncated = _truncate(items, max_items=5)

        assert len(result) == 5
        assert was_truncated is True

    def test_no_truncation_when_within_limit(self, sample_memory_item):
        """
        Given: Fewer items than max_items
        When: Truncating
        Then: All items are kept, truncated flag is False
        """
        items = [sample_memory_item(created_at=i) for i in range(3)]

        result, was_truncated = _truncate(items, max_items=5)

        assert len(result) == 3
        assert was_truncated is False

    def test_exact_limit_no_truncation(self, sample_memory_item):
        """
        Given: Exactly max_items items
        When: Truncating
        Then: All items are kept, truncated flag is False
        """
        items = [sample_memory_item(created_at=i) for i in range(5)]

        result, was_truncated = _truncate(items, max_items=5)

        assert len(result) == 5
        assert was_truncated is False


@pytest.mark.asyncio
class TestAssembleContext:
    """Tests for assemble_context function."""

    async def test_assembles_with_all_sources(
        self, memory_config, sample_memory_item
    ):
        """
        Given: Storage with SHORT, SHARED, and searchable memories
        When: Assembling context with search query
        Then: All sources are combined, deduplicated, and sorted
        """
        storage = AsyncMock()

        # Mock storage responses
        storage.query_by_task.side_effect = [
            [sample_memory_item(type_=MemoryType.SHORT, created_at=3000)],
            [sample_memory_item(type_=MemoryType.SHARED, created_at=2000)],
        ]
        storage.search_keyword.return_value = [
            sample_memory_item(type_=MemoryType.LONG, created_at=1000)
        ]

        result = await assemble_context(
            storage,
            memory_config,
            task_id="task-1",
            include_shared=True,
            query="test"
        )

        assert len(result.items) == 3
        assert result.items[0].type == MemoryType.SHORT
        assert result.items[1].type == MemoryType.SHARED
        assert result.items[2].type == MemoryType.LONG

    async def test_skips_shared_when_not_included(
        self, memory_config, sample_memory_item
    ):
        """
        Given: include_shared=False
        When: Assembling context
        Then: SHARED memories are not fetched
        """
        storage = AsyncMock()
        storage.query_by_task.return_value = [
            sample_memory_item(type_=MemoryType.SHORT)
        ]

        result = await assemble_context(
            storage,
            memory_config,
            task_id="task-1",
            include_shared=False,
            query=None
        )

        # Only called once for SHORT memories
        assert storage.query_by_task.call_count == 1

    async def test_skips_search_when_no_query(
        self, memory_config, sample_memory_item
    ):
        """
        Given: query=None
        When: Assembling context
        Then: Search is not performed
        """
        storage = AsyncMock()
        storage.query_by_task.side_effect = [
            [sample_memory_item(type_=MemoryType.SHORT)],
            [],
        ]

        result = await assemble_context(
            storage,
            memory_config,
            task_id="task-1",
            include_shared=True,
            query=None
        )

        storage.search_keyword.assert_not_called()

    async def test_truncates_to_max_items(
        self, memory_config, sample_memory_item
    ):
        """
        Given: More memories than max_items_per_context
        When: Assembling context
        Then: Result is truncated and truncated flag is set
        """
        storage = AsyncMock()
        storage.query_by_task.side_effect = [
            [sample_memory_item(created_at=i) for i in range(25)],
            [],
        ]

        memory_config.max_items_per_context = 20

        result = await assemble_context(
            storage,
            memory_config,
            task_id="task-1",
            include_shared=True,
            query=None
        )

        assert len(result.items) == 20
        assert result.truncated is True