"""
Integration test: Concurrent update scenarios.
"""
import pytest
from agent_os.common import TaskStatus, InvalidStatusTransitionError
from tests.utils.async_helpers import run_concurrent, count_exceptions, count_successes


@pytest.mark.asyncio
class TestConcurrentUpdates:
    """Test concurrency control mechanisms."""
    
    async def test_concurrent_resume_only_one_succeeds(self, task_center):
        """Only one of multiple concurrent resume calls should succeed."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        
        # Launch 10 concurrent resume attempts
        async def attempt_resume():
            await task_center.resume_task(task.id, {"input": "data"})
        
        tasks = [attempt_resume for _ in range(10)]
        results = await run_concurrent(tasks)
        
        # Only 1 should succeed, rest should get InvalidStatusTransitionError
        success_count = count_successes(results)
        error_count = count_exceptions(results, InvalidStatusTransitionError)
        
        assert success_count == 1
        assert error_count == 9
    
    async def test_concurrent_metadata_updates_converge(self, task_center):
        """Concurrent metadata updates should eventually succeed."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role",
            metadata={"counter": 0}
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Launch concurrent metadata updates
        async def update_metadata(i):
            await task_center.update_task_metadata(task.id, {f"key_{i}": f"value_{i}"})
        
        tasks = [lambda i=i: update_metadata(i) for i in range(5)]
        results = await run_concurrent(tasks)
        
        # All should succeed (via retry mechanism)
        success_count = count_successes(results)
        assert success_count == 5
        
        # Final metadata should contain all keys
        final_task = await task_center.get_task(task.id)
        for i in range(5):
            assert f"key_{i}" in final_task.metadata
    
    async def test_concurrent_runtime_state_updates_succeed(self, task_center):
        """Concurrent runtime state updates should succeed via retry."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Launch concurrent runtime state updates
        async def update_runtime(i):
            await task_center.update_task_runtime_state(task.id, {f"field_{i}": i})
        
        tasks = [lambda i=i: update_runtime(i) for i in range(5)]
        results = await run_concurrent(tasks)
        
        # All should succeed
        success_count = count_successes(results)
        assert success_count == 5
        
        # Final state should contain all fields
        final_state = await task_center.get_task_runtime_state(task.id)
        for i in range(5):
            assert f"field_{i}" in final_state.runtime_data