"""
Integration tests for large content handling.

Tests serialization, storage, and retrieval of large memory items.
"""

import pytest

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestLargeContentHandling:
    """Tests for handling large content in memory items."""

    async def test_large_content_under_1mb(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with ~500KB content
        When: Saving and retrieving
        Then: Content is stored and retrieved correctly
        
        Document 0: Large content serialization support
        """
        # Create ~500KB of text content
        large_text = "x" * (500 * 1024)  # 500KB
        
        item = sample_memory_item(
            content={"large_text": large_text, "size": "500KB"}
        )
        
        await postgres_storage.save(item)
        
        results = await postgres_storage.query_by_task(item.task_id)
        
        assert len(results) == 1
        assert len(results[0].content["large_text"]) == 500 * 1024
        assert results[0].content["size"] == "500KB"

    async def test_large_content_1mb(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with ~1MB content
        When: Saving and retrieving
        Then: Content is stored successfully
        
        Document 0: MemoryItem with >1MB content acceptance test
        """
        # Create ~1MB of text content
        large_text = "y" * (1024 * 1024)  # 1MB
        
        item = sample_memory_item(
            content={"large_text": large_text, "size": "1MB"}
        )
        
        await postgres_storage.save(item)
        
        results = await postgres_storage.query_by_task(item.task_id)
        
        assert len(results) == 1
        assert len(results[0].content["large_text"]) == 1024 * 1024

    async def test_large_nested_json_content(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with deeply nested large JSON
        When: Saving and retrieving
        Then: Structure is preserved
        """
        # Create nested structure with large arrays
        large_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "data_array": [
                            {"index": i, "value": f"value_{i}" * 100}
                            for i in range(1000)
                        ]
                    }
                }
            }
        }
        
        item = sample_memory_item(content=large_nested)
        
        await postgres_storage.save(item)
        
        results = await postgres_storage.query_by_task(item.task_id)
        
        assert len(results) == 1
        assert len(results[0].content["level1"]["level2"]["level3"]["data_array"]) == 1000

    async def test_batch_write_with_large_items(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Batch of memories with large content
        When: Batch saving
        Then: All items persisted correctly
        """
        # Create 10 items with ~100KB each
        items = [
            sample_memory_item(
                task_id="task-large-batch",
                content={"text": "z" * (100 * 1024), "index": i}
            )
            for i in range(10)
        ]
        
        await postgres_storage.save_batch(items)
        
        results = await postgres_storage.query_by_task("task-large-batch")
        
        assert len(results) == 10
        for r in results:
            assert len(r.content["text"]) == 100 * 1024

    async def test_search_with_large_content_results(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Memories with large searchable content
        When: Searching by keyword
        Then: Search succeeds and returns large results
        """
        # Save items with large content containing keywords
        large_content = "keyword " * 10000 + " other text " * 10000
        
        await postgres_storage.save_batch([
            sample_memory_item(
                content={"text": large_content, "doc": i}
            )
            for i in range(5)
        ])
        
        results = await postgres_storage.search_keyword(
            query="keyword",
            task_id=None,
            top_k=5
        )
        
        assert len(results) == 5
        for r in results:
            assert "keyword" in r.content["text"]

    async def test_large_metadata_jsonb(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: MemoryItem with large metadata object
        When: Saving and retrieving
        Then: Metadata preserved in JSONB
        """
        large_metadata = {
            "config": {
                f"option_{i}": f"value_{i}" * 100
                for i in range(100)
            },
            "history": [
                {"step": i, "data": f"data_{i}" * 50}
                for i in range(100)
            ]
        }
        
        item = sample_memory_item(metadata=large_metadata)
        
        await postgres_storage.save(item)
        
        results = await postgres_storage.query_by_task(item.task_id)
        
        assert len(results) == 1
        assert len(results[0].metadata["config"]) == 100
        assert len(results[0].metadata["history"]) == 100


@pytest.mark.asyncio
class TestLargeContentPerformance:
    """Tests for performance with large content."""

    async def test_query_performance_with_large_content(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Task with multiple large memories
        When: Querying by task
        Then: Query completes in reasonable time
        """
        import time
        
        task_id = "task-large-perf"
        
        # Save 20 items with ~100KB each
        items = [
            sample_memory_item(
                task_id=task_id,
                content={"text": "a" * (100 * 1024), "index": i}
            )
            for i in range(20)
        ]
        await postgres_storage.save_batch(items)
        
        # Query should complete quickly
        start = time.time()
        results = await postgres_storage.query_by_task(task_id)
        elapsed = time.time() - start
        
        assert len(results) == 20
        assert elapsed < 2.0  # Should complete within 2 seconds

    async def test_context_building_with_large_items(
        self, postgres_storage, memory_config, llm_gateway_config, sample_memory_item
    ):
        """
        Given: Task with large memories
        When: Building context with truncation
        Then: Truncation works correctly with large items
        """
        from agent_os.memory_center import MemoryCenter
        
        task_id = "task-context-large"
        
        # Create memory center
        memory_center = MemoryCenter(
            storage=postgres_storage,
            config=memory_config,
            llm_gateway_config=llm_gateway_config,
        )
        
        # Save 30 large items
        items = [
            sample_memory_item(
                task_id=task_id,
                type_=MemoryType.SHORT,
                content={"text": "b" * (50 * 1024), "index": i},
                created_at=1000 + i
            )
            for i in range(30)
        ]
        await memory_center.write_batch(items)
        
        # Build context (max_items=20)
        context = await memory_center.build_context(task_id)
        
        assert len(context.items) == 20
        assert context.truncated is True
        # Newest items should be kept
        assert context.items[0].created_at == 1029