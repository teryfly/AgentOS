"""
Integration test: Full TaskCenter API coverage.
"""
import pytest
from agent_os.common import TaskStatus, TaskResult


@pytest.mark.asyncio
class TestTaskCenterAPI:
    """Test full TaskCenter public API."""
    
    async def test_full_lifecycle_workflow(self, task_center, sample_metadata):
        """Test complete lifecycle: create → run → complete."""
        # Create task
        task = await task_center.create_task(
            name="Full Lifecycle Test",
            description="Testing all operations",
            role="test_role",
            metadata=sample_metadata
        )
        
        assert task.status == TaskStatus.PENDING
        assert task.metadata["project_id"] == 42
        
        # Transition to RUNNING
        running = await task_center.update_status(task.id, TaskStatus.RUNNING)
        assert running.status == TaskStatus.RUNNING
        
        # Update metadata
        await task_center.update_task_metadata(task.id, {"new_key": "new_value"})
        
        # Update runtime state
        await task_center.update_task_runtime_state(task.id, {"step": 1})
        
        # Verify runtime state
        runtime_state = await task_center.get_task_runtime_state(task.id)
        assert runtime_state.runtime_data["step"] == 1
        
        # Complete task
        result = TaskResult(success=True, data={"output": "success"}, error=None)
        await task_center.complete_task(task.id, result)
        
        # Verify final state
        final = await task_center.get_task(task.id)
        assert final.status == TaskStatus.COMPLETED
        assert final.result.success is True
        assert final.metadata["new_key"] == "new_value"
    
    async def test_list_tasks_with_filters(self, task_center):
        """Test list_tasks with status and role filters."""
        # Create tasks with different statuses and roles
        await task_center.create_task("Task1", "Desc1", "role_a")
        task2 = await task_center.create_task("Task2", "Desc2", "role_b")
        await task_center.update_status(task2.id, TaskStatus.RUNNING)
        await task_center.create_task("Task3", "Desc3", "role_a")
        
        # Filter by status
        pending_tasks = await task_center.list_tasks(status=TaskStatus.PENDING)
        assert len(pending_tasks) == 2
        
        # Filter by role
        role_a_tasks = await task_center.list_tasks(role="role_a")
        assert len(role_a_tasks) == 2
        
        # Combined filter
        running_b = await task_center.list_tasks(status=TaskStatus.RUNNING, role="role_b")
        assert len(running_b) == 1
    
    async def test_get_runnable_tasks(self, task_center):
        """Test get_runnable_tasks returns correct subset."""
        # Create independent task (should be runnable)
        task1 = await task_center.create_task("Independent", "Desc", "role")
        
        # Create task with incomplete dependency (not runnable)
        dep = await task_center.create_task("Dependency", "Desc", "role")
        task2 = await task_center.create_task(
            "Dependent",
            "Desc",
            "role",
            depends_on=[dep.id]
        )
        
        runnable = await task_center.get_runnable_tasks()
        
        # Only task1 should be runnable
        runnable_ids = [t.id for t in runnable]
        assert task1.id in runnable_ids
        assert task2.id not in runnable_ids
    
    async def test_fail_task_workflow(self, task_center):
        """Test task failure workflow."""
        task = await task_center.create_task("Task", "Desc", "role")
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Fail task
        await task_center.fail_task(task.id, "Simulated error")
        
        # Verify failed state
        failed = await task_center.get_task(task.id)
        assert failed.status == TaskStatus.FAILED
        assert failed.result.success is False
        assert failed.result.error == "Simulated error"
    
    async def test_waiting_input_workflow(self, task_center):
        """Test WAITING_INPUT transition."""
        task = await task_center.create_task("Interactive", "Desc", "role")
        
        # Transition through states
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        waiting = await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        
        assert waiting.status == TaskStatus.WAITING_INPUT
        
        # Resume
        await task_center.resume_task(task.id, {"input": "value"})
        
        resumed = await task_center.get_task(task.id)
        assert resumed.status == TaskStatus.RUNNING
    
    async def test_delete_runtime_state(self, task_center):
        """Test manual runtime state deletion."""
        task = await task_center.create_task("Task", "Desc", "role")
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Create runtime state
        await task_center.update_task_runtime_state(task.id, {"data": "value"})
        
        # Verify exists
        state = await task_center.get_task_runtime_state(task.id)
        assert state is not None
        
        # Delete
        await task_center.delete_task_runtime_state(task.id)
        
        # Verify deleted
        state_after = await task_center.get_task_runtime_state(task.id)
        assert state_after is None