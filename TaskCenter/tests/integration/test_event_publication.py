"""
Integration test: Event publication completeness.

Verifies all 8 domain events are published at correct trigger points.
Ensures TaskCenter fulfills event-driven coordination contract.
"""
import pytest
from agent_os.common import (
    TaskStatus, TaskResult,
    TaskCreated, TaskStarted, TaskCompleted, TaskFailed,
    TaskWaitingInput, TaskWaitingDependency, TaskUnblocked, TaskResumed
)
from tests.utils.task_builder import TaskBuilder


@pytest.mark.asyncio
class TestEventPublicationCompleteness:
    """
    Verify all 8 domain events are published correctly.
    
    Mapping to Document 1 Section 7.1:
    - TaskCreated
    - TaskStarted
    - TaskCompleted
    - TaskFailed
    - TaskWaitingInput
    - TaskWaitingDependency
    - TaskUnblocked
    - TaskResumed
    """
    
    async def test_task_created_event_on_create_task(self, task_center):
        """TaskCreated should be published when create_task is called."""
        task = await task_center.create_task(
            name="Event Test",
            description="Test event publication",
            role="test_role"
        )
        
        events = task_center._event_bus.get_events_by_type(TaskCreated)
        assert len(events) == 1
        assert events[0].task_id == task.id
        assert events[0].name == "Event Test"
        assert events[0].role == "test_role"
        assert events[0].status == TaskStatus.PENDING
    
    async def test_task_started_event_on_status_to_running(self, task_center):
        """TaskStarted should be published when status transitions to RUNNING."""
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role"
        )
        
        # Clear creation event
        task_center._event_bus.clear()
        
        # Transition to RUNNING
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        events = task_center._event_bus.get_events_by_type(TaskStarted)
        assert len(events) == 1
        assert events[0].task_id == task.id
    
    async def test_task_completed_event_on_complete_task(self, task_center):
        """TaskCompleted should be published when task completes successfully."""
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear previous events
        task_center._event_bus.clear()
        
        result = TaskResult(success=True, data={"output": "done"}, error=None)
        await task_center.complete_task(task.id, result)
        
        events = task_center._event_bus.get_events_by_type(TaskCompleted)
        assert len(events) == 1
        assert events[0].task_id == task.id
        assert events[0].result.success is True
    
    async def test_task_failed_event_on_fail_task(self, task_center):
        """TaskFailed should be published when task fails."""
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear previous events
        task_center._event_bus.clear()
        
        await task_center.fail_task(task.id, "Test error")
        
        events = task_center._event_bus.get_events_by_type(TaskFailed)
        assert len(events) == 1
        assert events[0].task_id == task.id
        assert events[0].error == "Test error"
    
    async def test_task_waiting_input_event_on_status_transition(self, task_center):
        """TaskWaitingInput should be published when status transitions to WAITING_INPUT."""
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear previous events
        task_center._event_bus.clear()
        
        # Transition to WAITING_INPUT
        await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        
        events = task_center._event_bus.get_events_by_type(TaskWaitingInput)
        assert len(events) == 1
        assert events[0].task_id == task.id
    
    async def test_task_waiting_dependency_event_on_explicit_transition(self, task_center):
        """
        TaskWaitingDependency should be published when explicitly transitioning to WAITING_DEPENDENCY.
        
        Note: Normally this status is auto-assigned at creation, but can be set explicitly
        during execution (e.g., GroupActor detecting new dependencies).
        """
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear previous events
        task_center._event_bus.clear()
        
        # Explicitly transition to WAITING_DEPENDENCY
        await task_center.update_status(task.id, TaskStatus.WAITING_DEPENDENCY)
        
        events = task_center._event_bus.get_events_by_type(TaskWaitingDependency)
        assert len(events) == 1
        assert events[0].task_id == task.id
    
    async def test_task_unblocked_event_on_dependency_completion(self, task_center):
        """TaskUnblocked should be published when dependencies are satisfied."""
        # Create parent task
        parent = await task_center.create_task(
            name="Parent",
            description="Parent task",
            role="parent_role"
        )
        
        # Transition parent to RUNNING
        await task_center.update_status(parent.id, TaskStatus.RUNNING)
        
        # Create child depending on parent
        child = await task_center.create_task(
            name="Child",
            description="Child task",
            role="child_role",
            depends_on=[parent.id]
        )
        
        # Child should be WAITING_DEPENDENCY
        assert child.status == TaskStatus.WAITING_DEPENDENCY
        
        # Clear events
        task_center._event_bus.clear()
        
        # Complete parent
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(parent.id, result)
        
        # Should publish TaskUnblocked for child
        unblocked_events = task_center._event_bus.get_events_by_type(TaskUnblocked)
        assert len(unblocked_events) == 1
        assert unblocked_events[0].task_id == child.id
    
    async def test_task_resumed_event_on_resume_task(self, task_center):
        """TaskResumed should be published when resume_task is called."""
        task = await task_center.create_task(
            name="Interactive Task",
            description="Needs input",
            role="interactive_role"
        )
        
        # Transition to RUNNING then WAITING_INPUT
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        
        # Clear previous events
        task_center._event_bus.clear()
        
        # Resume with input
        input_data = {"user_choice": "option_a"}
        await task_center.resume_task(task.id, input_data)
        
        events = task_center._event_bus.get_events_by_type(TaskResumed)
        assert len(events) == 1
        assert events[0].task_id == task.id
        assert events[0].input_data == input_data
    
    async def test_no_event_on_metadata_update(self, task_center):
        """Metadata updates should NOT publish domain events (per Document 1)."""
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role",
            metadata={"key1": "value1"}
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear all previous events
        task_center._event_bus.clear()
        
        # Update metadata
        await task_center.update_task_metadata(task.id, {"key2": "value2"})
        
        # No events should be published
        assert len(task_center._event_bus.published_events) == 0
    
    async def test_no_event_on_runtime_state_update(self, task_center):
        """Runtime state updates should NOT publish domain events (per Document 1)."""
        task = await task_center.create_task(
            name="Test",
            description="Desc",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear all previous events
        task_center._event_bus.clear()
        
        # Update runtime state
        await task_center.update_task_runtime_state(task.id, {"step": 1})
        
        # No events should be published
        assert len(task_center._event_bus.published_events) == 0


@pytest.mark.asyncio
class TestEventSequenceScenarios:
    """
    Test event sequences in common scenarios.
    
    Ensures event ordering and completeness in real workflows.
    """
    
    async def test_simple_task_lifecycle_events(self, task_center):
        """Verify event sequence: Created → Started → Completed."""
        task = await task_center.create_task(
            name="Simple Task",
            description="Test",
            role="role"
        )
        
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(task.id, result)
        
        # Verify event sequence
        all_events = task_center._event_bus.published_events
        event_types = [type(e).__name__ for e in all_events]
        
        assert "TaskCreated" in event_types
        assert "TaskStarted" in event_types
        assert "TaskCompleted" in event_types
        
        # Verify order
        created_idx = event_types.index("TaskCreated")
        started_idx = event_types.index("TaskStarted")
        completed_idx = event_types.index("TaskCompleted")
        
        assert created_idx < started_idx < completed_idx
    
    async def test_dependency_chain_events(self, task_center):
        """Verify event sequence: Parent completes → Child unblocked."""
        parent = await task_center.create_task(
            name="Parent",
            description="Parent",
            role="role"
        )
        
        child = await task_center.create_task(
            name="Child",
            description="Child",
            role="role",
            depends_on=[parent.id]
        )
        
        # Clear creation events
        task_center._event_bus.clear()
        
        # Complete parent
        await task_center.update_status(parent.id, TaskStatus.RUNNING)
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(parent.id, result)
        
        # Should have: Started → Completed → Unblocked
        all_events = task_center._event_bus.published_events
        event_types = [type(e).__name__ for e in all_events]
        
        assert "TaskStarted" in event_types
        assert "TaskCompleted" in event_types
        assert "TaskUnblocked" in event_types
        
        # Verify Unblocked comes after Completed
        completed_idx = event_types.index("TaskCompleted")
        unblocked_idx = event_types.index("TaskUnblocked")
        assert completed_idx < unblocked_idx
    
    async def test_wait_input_resume_events(self, task_center):
        """Verify event sequence: Started → WaitingInput → Resumed → Completed."""
        task = await task_center.create_task(
            name="Interactive",
            description="Test",
            role="role"
        )
        
        # Clear creation event
        task_center._event_bus.clear()
        
        # Run → Wait → Resume → Complete
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.update_status(task.id, TaskStatus.WAITING_INPUT)
        await task_center.resume_task(task.id, {"input": "data"})
        
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(task.id, result)
        
        # Verify all events present
        event_types = [type(e).__name__ for e in task_center._event_bus.published_events]
        
        assert "TaskStarted" in event_types
        assert "TaskWaitingInput" in event_types
        assert "TaskResumed" in event_types
        assert "TaskCompleted" in event_types