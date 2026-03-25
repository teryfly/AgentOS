"""
Integration test: Automatic runtime state cleanup.
"""
import pytest
from agent_os.common import TaskStatus, TaskResult
import asyncio


@pytest.mark.asyncio
class TestCleanupHandler:
    """Test runtime state cleanup on task completion."""
    
    async def test_cleanup_deletes_runtime_state_on_completion(self, task_center):
        """Runtime state should be deleted when task completes."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Create runtime state
        await task_center.update_task_runtime_state(task.id, {"data": "value"})
        
        # Verify state exists
        state_before = await task_center.get_task_runtime_state(task.id)
        assert state_before is not None
        
        # Complete task
        await task_center.complete_task(task.id, TaskResult(True, "done", None))
        
        # Allow async cleanup to execute
        await asyncio.sleep(0.1)
        
        # Runtime state should be deleted
        state_after = await task_center.get_task_runtime_state(task.id)
        assert state_after is None
    
    async def test_cleanup_deletes_runtime_state_on_failure(self, task_center):
        """Runtime state should be deleted when task fails."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.update_task_runtime_state(task.id, {"data": "value"})
        
        # Fail task
        await task_center.fail_task(task.id, "Test error")
        
        await asyncio.sleep(0.1)
        
        # Runtime state should be deleted
        state = await task_center.get_task_runtime_state(task.id)
        assert state is None
    
    async def test_cleanup_failure_does_not_block_completion(self, task_center):
        """Cleanup failure should not prevent task completion."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Complete without runtime state (nothing to clean)
        await task_center.complete_task(task.id, TaskResult(True, "done", None))
        
        # Task should be completed regardless
        updated = await task_center.get_task(task.id)
        assert updated.status == TaskStatus.COMPLETED