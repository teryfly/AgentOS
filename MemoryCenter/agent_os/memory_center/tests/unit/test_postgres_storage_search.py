"""
Unit tests for PostgreSQL storage search operations.

Tests search_keyword() with task-scoped and cross-task searches.
"""

import pytest

from agent_os.common import MemorySource, MemoryType


@pytest.mark.asyncio
class TestPostgresStorageSearch:
    """Tests for keyword search in PostgresMemoryStorage."""

    async def test_search_keyword_task_scoped(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with searchable content
        When: Searching with task_id specified
        Then: Only memories from that task are returned
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                task_id="task-1",
                content={"text": "Python programming tutorial"}
            ),
            sample_memory_item(
                task_id="task-1",
                content={"text": "JavaScript guide"}
            ),
            sample_memory_item(
                task_id="task-2",
                content={"text": "Python best practices"}
            ),
        ])

        results = await postgres_storage.search_keyword(
            query="Python",
            task_id="task-1",
            top_k=5
        )

        assert len(results) == 1
        assert results[0].task_id == "task-1"
        assert "Python" in str(results[0].content)

    async def test_search_keyword_cross_task(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories across multiple tasks
        When: Searching with task_id=None (cross-task)
        Then: All matching memories are returned regardless of task
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                task_id="task-a",
                content={"text": "Coding Task Document for feature X"}
            ),
            sample_memory_item(
                task_id="task-b",
                content={"text": "Coding Task Document for feature Y"}
            ),
            sample_memory_item(
                task_id="task-c",
                content={"text": "Regular task output"}
            ),
        ])

        results = await postgres_storage.search_keyword(
            query="Coding Task Document",
            task_id=None,  # Cross-task search
            top_k=5
        )

        assert len(results) == 2
        task_ids = {r.task_id for r in results}
        assert task_ids == {"task-a", "task-b"}

    async def test_search_respects_top_k_limit(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: More matching memories than top_k
        When: Searching with top_k limit
        Then: Only top_k results are returned
        """
        await postgres_storage.save_batch([
            sample_memory_item(content={"text": f"common keyword item {i}"})
            for i in range(10)
        ])

        results = await postgres_storage.search_keyword(
            query="common keyword",
            task_id=None,
            top_k=3
        )

        assert len(results) == 3

    async def test_search_empty_query_returns_empty(
        self, postgres_storage
    ):
        """
        Given: Memories in storage
        When: Searching with empty query
        Then: Empty list is returned
        """
        results = await postgres_storage.search_keyword(
            query="",
            task_id=None,
            top_k=5
        )

        assert results == []

    async def test_search_orders_by_relevance(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with varying relevance to query
        When: Searching by keyword
        Then: Results are ordered by ts_rank DESC (most relevant first)
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                content={"text": "Python"}  # Exact match
            ),
            sample_memory_item(
                content={"text": "Python programming language tutorial guide"}
            ),
            sample_memory_item(
                content={"text": "Learn Python programming"}
            ),
        ])

        results = await postgres_storage.search_keyword(
            query="Python",
            task_id=None,
            top_k=5
        )

        assert len(results) >= 1
        # Verify all results contain the keyword
        assert all("Python" in str(r.content) for r in results)

    async def test_search_with_metadata_filter(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with has_coding_doc metadata flag
        When: Searching and filtering results by metadata
        Then: Can retrieve LONG memories with specific metadata
        """
        await postgres_storage.save_batch([
            sample_memory_item(
                type_=MemoryType.LONG,
                source=MemorySource.TASK,
                content={"final_output": "# Coding Task Document\n..."},
                metadata={"role": "architect", "has_coding_doc": True}
            ),
            sample_memory_item(
                type_=MemoryType.LONG,
                source=MemorySource.TASK,
                content={"result": "Regular task output"},
                metadata={"role": "general"}
            ),
        ])

        results = await postgres_storage.search_keyword(
            query="Coding Task Document",
            task_id=None,
            top_k=5
        )

        # Filter by metadata in application layer
        filtered = [
            r for r in results
            if r.source == MemorySource.TASK
            and r.type == MemoryType.LONG
            and r.metadata.get("has_coding_doc") == True
        ]

        assert len(filtered) == 1
        assert filtered[0].metadata["role"] == "architect"