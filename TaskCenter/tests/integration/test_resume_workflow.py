"""
Integration test: WAIT_INPUT → Resume workflow.
"""
import pytest
from agent_os.common import TaskStatus, TaskResumed, InvalidStatusTransitionError


@pytest.mark.asyncio
class TestResumeWorkflow:
    """Test task resumption from WAITING_INPUT."""
    
    async def test_resume_task_from_waiting_input(self, task_center):
        """Should resume task from WAITING_INPUT."""
        task = await task_center.create_task(
            name="Interactive Task",
            description="Needs input",
            role="interactive_role"
        )
        
        # Transition to RUNNING then WAITING_INPUT
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        
        # Resume with input
        input_data = {"user_choice": "option_a"}
        await task_center.resume_task(task.id, input_data)
        
        # Should be RUNNING again
        updated = await task_center.get_task(task.id)
        assert updated.status == TaskStatus.RUNNING
        
        # Verify event published with input_data
        events = task_center._event_bus.get_events_by_type(TaskResumed)
        assert len(events) == 1
        assert events[0].input_data == input_data
    
    async def test_resume_rejects_non_waiting_task(self, task_center):
        """Should reject resume for non-WAITING_INPUT task."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role"
        )
        
        # Task is PENDING, cannot resume
        with pytest.raises(InvalidStatusTransitionError):
            await task_center.resume_task(task.id, {"data": "value"})
    
    async def test_input_data_not_persisted_to_metadata(self, task_center):
        """Input data should not be written to task.metadata."""
        task = await task_center.create_task(
            name="Task",
            description="Desc",
            role="role",
            metadata={"project_id": 42}
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        
        input_data = {"user_input": "test_value"}
        await task_center.resume_task(task.id, input_data)
        
        # Metadata should not contain input_data
        updated = await task_center.get_task(task.id)
        assert "user_input" not in updated.metadata
        assert updated.metadata["project_id"] == 42