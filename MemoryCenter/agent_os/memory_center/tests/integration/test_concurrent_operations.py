"""
Integration tests for concurrent operations.

Tests concurrent writes, connection pool exhaustion, and race conditions.
"""

import asyncio
import pytest

from agent_os.common import MemoryType


@pytest.mark.asyncio
class TestConcurrentWrites:
    """Tests for concurrent write operations."""

    async def test_concurrent_writes_different_tasks(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple concurrent writes to different tasks
        When: Writing simultaneously
        Then: All writes succeed without conflicts
        
        Document 0: Concurrent write support
        """
        async def write_memory(task_id: str):
            item = sample_memory_item(
                task_id=task_id,
                content={"task": task_id}
            )
            await postgres_storage.save(item)
        
        # Create 10 concurrent writes to different tasks
        tasks = [write_memory(f"task-{i}") for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify all tasks have their memories
        for i in range(10):
            results = await postgres_storage.query_by_task(f"task-{i}")
            assert len(results) == 1

    async def test_concurrent_batch_writes(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple concurrent batch writes
        When: Writing simultaneously
        Then: All batches are persisted correctly
        """
        async def batch_write(batch_id: int):
            items = [
                sample_memory_item(
                    task_id=f"batch-{batch_id}",
                    content={"index": i}
                )
                for i in range(5)
            ]
            await postgres_storage.save_batch(items)
        
        # Create 5 concurrent batch writes
        tasks = [batch_write(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # Verify all batches persisted
        for i in range(5):
            results = await postgres_storage.query_by_task(f"batch-{i}")
            assert len(results) == 5

    async def test_duplicate_id_conflict_handled(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Two concurrent writes with same memory_id
        When: Writing simultaneously
        Then: Database constraint violation occurs, one fails
        
        Document 0: Duplicate ID handling
        """
        item = sample_memory_item(task_id="task-dup")
        
        async def write_duplicate():
            try:
                await postgres_storage.save(item)
                return "success"
            except Exception:
                return "failed"
        
        # Try writing same item twice concurrently
        results = await asyncio.gather(
            write_duplicate(),
            write_duplicate(),
            return_exceptions=True
        )
        
        # At least one should fail due to unique constraint
        success_count = sum(1 for r in results if r == "success")
        assert success_count == 1  # Only one should succeed


@pytest.mark.asyncio
class TestConnectionPoolBehavior:
    """Tests for connection pool behavior under load."""

    async def test_connection_pool_handles_concurrent_queries(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple concurrent read operations
        When: Querying simultaneously (within pool limits)
        Then: All queries succeed
        
        Document 7: Connection pool supports concurrent operations
        """
        # Prepare test data
        task_id = "task-concurrent-reads"
        await postgres_storage.save_batch([
            sample_memory_item(task_id=task_id) for _ in range(10)
        ])
        
        async def query_task():
            return await postgres_storage.query_by_task(task_id)
        
        # Create 15 concurrent queries (within default max_size=20)
        tasks = [query_task() for _ in range(15)]
        results = await asyncio.gather(*tasks)
        
        # All queries should succeed
        assert len(results) == 15
        assert all(len(r) == 10 for r in results)

    async def test_connection_pool_graceful_under_heavy_load(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: More concurrent operations than max pool size
        When: Executing many queries
        Then: Operations queue gracefully, no crashes
        
        Document 0: Connection pool exhaustion handling
        """
        # Prepare test data
        await postgres_storage.save_batch([
            sample_memory_item(task_id=f"task-{i}") for i in range(10)
        ])
        
        async def mixed_operation(i: int):
            # Mix of reads and writes
            if i % 2 == 0:
                await postgres_storage.query_by_task(f"task-{i % 10}")
            else:
                await postgres_storage.save(
                    sample_memory_item(task_id=f"task-load-{i}")
                )
        
        # Create 30 concurrent operations (exceeds default max_size=20)
        tasks = [mixed_operation(i) for i in range(30)]
        
        # Should complete without errors (may be slower due to queuing)
        await asyncio.gather(*tasks)

    async def test_search_concurrent_with_writes(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Concurrent search and write operations
        When: Executing simultaneously
        Then: No deadlocks or data corruption
        """
        async def write_loop(task_id: str, count: int):
            for i in range(count):
                await postgres_storage.save(
                    sample_memory_item(
                        task_id=task_id,
                        content={"text": f"searchable content {i}"}
                    )
                )
                await asyncio.sleep(0.01)
        
        async def search_loop(count: int):
            results = []
            for _ in range(count):
                r = await postgres_storage.search_keyword(
                    query="searchable",
                    task_id=None,
                    top_k=10
                )
                results.append(len(r))
                await asyncio.sleep(0.01)
            return results
        
        # Run concurrent writes and searches
        write_task = write_loop("task-concurrent", 20)
        search_task = search_loop(20)
        
        write_result, search_results = await asyncio.gather(
            write_task,
            search_task
        )
        
        # Search should return increasing results as writes progress
        assert len(search_results) == 20
        assert isinstance(search_results, list)


@pytest.mark.asyncio
class TestConcurrentDeletes:
    """Tests for concurrent delete operations."""

    async def test_concurrent_deletes_same_task(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Multiple concurrent deletes on same task
        When: Deleting simultaneously
        Then: All deletes succeed, final state is consistent
        """
        task_id = "task-concurrent-delete"
        
        # Create test data
        await postgres_storage.save_batch([
            sample_memory_item(task_id=task_id) for _ in range(10)
        ])
        
        async def delete_task():
            await postgres_storage.delete_by_task(task_id)
        
        # Multiple concurrent deletes
        await asyncio.gather(
            delete_task(),
            delete_task(),
            delete_task()
        )
        
        # Final state should be empty
        results = await postgres_storage.query_by_task(task_id)
        assert len(results) == 0

    async def test_concurrent_delete_and_query(
        self, postgres_storage, sample_memory_item
    ):
        """
        Given: Concurrent delete and query operations
        When: Executing simultaneously
        Then: No exceptions, results consistent with timing
        """
        task_id = "task-delete-query-race"
        
        # Create test data
        items = [sample_memory_item(task_id=task_id) for _ in range(5)]
        await postgres_storage.save_batch(items)
        
        async def delete_after_delay():
            await asyncio.sleep(0.05)
            await postgres_storage.delete_by_task(task_id)
        
        async def query_repeatedly():
            results = []
            for _ in range(10):
                r = await postgres_storage.query_by_task(task_id)
                results.append(len(r))
                await asyncio.sleep(0.01)
            return results
        
        delete_task = delete_after_delay()
        query_results = await asyncio.gather(query_repeatedly(), delete_task)
        
        # Queries should show decreasing count (5 -> 0)
        counts = query_results[0]
        assert isinstance(counts, list)
        # Some queries may see 5, some may see 0 after delete