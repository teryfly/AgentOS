"""
Integration test: Create → Complete → Unblock workflow.
"""
import pytest
from agent_os.common import TaskStatus, TaskResult, TaskCreated, TaskCompleted, TaskUnblocked


@pytest.mark.asyncio
class TestCreateCompleteWorkflow:
    """Test end-to-end task lifecycle."""
    
    async def test_create_task_publishes_event(self, task_center):
        """Creating task should publish TaskCreated event."""
        task = await task_center.create_task(
            name="Test Task",
            description="Description",
            role="test_role"
        )
        
        assert task.status == TaskStatus.PENDING
        
        # Verify event published
        events = task_center._event_bus.get_events_by_type(TaskCreated)
        assert len(events) == 1
        assert events[0].task_id == task.id
    
    async def test_complete_task_unblocks_dependent(self, task_center):
        """Completing task should unblock waiting dependents."""
        # Create parent task
        parent = await task_center.create_task(
            name="Parent",
            description="Parent task",
            role="parent_role"
        )
        
        # Transition to RUNNING
        await task_center.update_status(parent.id, TaskStatus.RUNNING)
        
        # Create dependent task
        child = await task_center.create_task(
            name="Child",
            description="Child task",
            role="child_role",
            depends_on=[parent.id]
        )
        
        # Child should be WAITING_DEPENDENCY
        assert child.status == TaskStatus.WAITING_DEPENDENCY
        
        # Complete parent
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(parent.id, result)
        
        # Child should be unblocked
        child_updated = await task_center.get_task(child.id)
        assert child_updated.status == TaskStatus.PENDING
        
        # Verify events
        completed_events = task_center._event_bus.get_events_by_type(TaskCompleted)
        unblocked_events = task_center._event_bus.get_events_by_type(TaskUnblocked)
        assert len(completed_events) == 1
        assert len(unblocked_events) == 1
    
    async def test_multiple_dependents_unblocked(self, task_center):
        """Multiple dependents should all be unblocked."""
        parent = await task_center.create_task(
            name="Parent",
            description="Parent",
            role="role"
        )
        
        await task_center.update_status(parent.id, TaskStatus.RUNNING)
        
        # Create multiple children
        child1 = await task_center.create_task(
            name="Child1",
            description="Child 1",
            role="role",
            depends_on=[parent.id]
        )
        
        child2 = await task_center.create_task(
            name="Child2",
            description="Child 2",
            role="role",
            depends_on=[parent.id]
        )
        
        # Complete parent
        await task_center.complete_task(parent.id, TaskResult(True, "done", None))
        
        # Both children should be unblocked
        child1_updated = await task_center.get_task(child1.id)
        child2_updated = await task_center.get_task(child2.id)
        assert child1_updated.status == TaskStatus.PENDING
        assert child2_updated.status == TaskStatus.PENDING