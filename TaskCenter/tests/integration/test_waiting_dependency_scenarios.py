"""
Integration test: WAITING_DEPENDENCY status and event publication.

Covers both implicit (creation-time) and explicit (runtime) transitions.
Ensures TaskWaitingDependency event is published in all scenarios.
"""
import pytest
from agent_os.common import TaskStatus, TaskWaitingDependency
from tests.utils.task_builder import BatchItemBuilder


@pytest.mark.asyncio
class TestWaitingDependencyImplicit:
    """
    Test implicit WAITING_DEPENDENCY assignment at task creation.
    
    Per Document 1 Section 4.3:
    Initial status is WAITING_DEPENDENCY when dependencies are not all COMPLETED.
    """
    
    async def test_single_task_with_pending_dependency(self, task_center):
        """Task depending on PENDING task should be WAITING_DEPENDENCY."""
        # Create dependency (PENDING by default)
        dep = await task_center.create_task(
            name="Dependency",
            description="Dep",
            role="role"
        )
        
        # Clear creation event
        task_center._event_bus.clear()
        
        # Create dependent task
        child = await task_center.create_task(
            name="Child",
            description="Child",
            role="role",
            depends_on=[dep.id]
        )
        
        # Should be WAITING_DEPENDENCY
        assert child.status == TaskStatus.WAITING_DEPENDENCY
        
        # Should publish TaskCreated (with WAITING_DEPENDENCY status)
        from agent_os.common import TaskCreated
        created_events = task_center._event_bus.get_events_by_type(TaskCreated)
        assert len(created_events) == 1
        assert created_events[0].status == TaskStatus.WAITING_DEPENDENCY
    
    async def test_batch_with_internal_dependencies(self, task_center):
        """Batch items depending on each other should be WAITING_DEPENDENCY."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build(),
            BatchItemBuilder().with_ref_id("task3").depends_on_refs("task2").build()
        ]
        
        result = await task_center.create_task_batch(items)
        
        # task1 should be PENDING (no deps)
        assert result["task1"].status == TaskStatus.PENDING
        
        # task2, task3 should be WAITING_DEPENDENCY (internal deps)
        assert result["task2"].status == TaskStatus.WAITING_DEPENDENCY
        assert result["task3"].status == TaskStatus.WAITING_DEPENDENCY
    
    async def test_task_with_running_dependency(self, task_center):
        """Task depending on RUNNING task should be WAITING_DEPENDENCY."""
        # Create and start dependency
        dep = await task_center.create_task(
            name="Dependency",
            description="Dep",
            role="role"
        )
        await task_center.update_status(dep.id, TaskStatus.RUNNING)
        
        # Create dependent task
        child = await task_center.create_task(
            name="Child",
            description="Child",
            role="role",
            depends_on=[dep.id]
        )
        
        # Should be WAITING_DEPENDENCY
        assert child.status == TaskStatus.WAITING_DEPENDENCY


@pytest.mark.asyncio
class TestWaitingDependencyExplicit:
    """
    Test explicit transition to WAITING_DEPENDENCY during runtime.
    
    Per Document 1 Section 4.1:
    RUNNING → WAITING_DEPENDENCY is a legal transition.
    """
    
    async def test_explicit_transition_publishes_event(self, task_center):
        """
        Explicitly transitioning to WAITING_DEPENDENCY should publish event.
        
        Use case: GroupActor detects new dependencies during execution.
        """
        task = await task_center.create_task(
            name="Dynamic Dependency",
            description="Discovers deps at runtime",
            role="role"
        )
        
        # Start task
        await task_center.update_status(task.id, TaskStatus.RUNNING)
        
        # Clear events
        task_center._event_bus.clear()
        
        # Explicitly transition to WAITING_DEPENDENCY
        await task_center.update_status(task.id, TaskStatus.WAITING_DEPENDENCY)
        
        # Should publish TaskWaitingDependency event
        events = task_center._event_bus.get_events_by_type(TaskWaitingDependency)
        assert len(events) == 1
        assert events[0].task_id == task.id
    
    async def test_waiting_dependency_to_pending_unblock(self, task_center):
        """
        WAITING_DEPENDENCY → PENDING should publish TaskUnblocked.
        
        This tests the unblock path independent of completion.
        """
        # Create parent
        parent = await task_center.create_task(
            name="Parent",
            description="Parent",
            role="role"
        )
        await task_center.update_status(parent.id, TaskStatus.RUNNING)
        
        # Create child (will be WAITING_DEPENDENCY)
        child = await task_center.create_task(
            name="Child",
            description="Child",
            role="role",
            depends_on=[parent.id]
        )
        
        assert child.status == TaskStatus.WAITING_DEPENDENCY
        
        # Clear events
        task_center._event_bus.clear()
        
        # Complete parent
        from agent_os.common import TaskResult, TaskUnblocked
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(parent.id, result)
        
        # Should publish TaskUnblocked
        unblocked_events = task_center._event_bus.get_events_by_type(TaskUnblocked)
        assert len(unblocked_events) == 1
        assert unblocked_events[0].task_id == child.id
        
        # Verify child is now PENDING
        updated_child = await task_center.get_task(child.id)
        assert updated_child.status == TaskStatus.PENDING


@pytest.mark.asyncio
class TestWaitingDependencyEdgeCases:
    """
    Test edge cases for WAITING_DEPENDENCY status.
    """
    
    async def test_multiple_dependencies_partial_completion(self, task_center):
        """Task with multiple deps should remain WAITING_DEPENDENCY until all complete."""
        # Create two dependencies
        dep1 = await task_center.create_task(
            name="Dep1",
            description="First dependency",
            role="role"
        )
        dep2 = await task_center.create_task(
            name="Dep2",
            description="Second dependency",
            role="role"
        )
        
        # Create task depending on both
        task = await task_center.create_task(
            name="Multi-Dep Task",
            description="Depends on two",
            role="role",
            depends_on=[dep1.id, dep2.id]
        )
        
        assert task.status == TaskStatus.WAITING_DEPENDENCY
        
        # Complete first dependency
        await task_center.update_status(dep1.id, TaskStatus.RUNNING)
        from agent_os.common import TaskResult
        result = TaskResult(success=True, data="done", error=None)
        await task_center.complete_task(dep1.id, result)
        
        # Task should STILL be WAITING_DEPENDENCY
        updated_task = await task_center.get_task(task.id)
        assert updated_task.status == TaskStatus.WAITING_DEPENDENCY
        
        # Complete second dependency
        await task_center.update_status(dep2.id, TaskStatus.RUNNING)
        await task_center.complete_task(dep2.id, result)
        
        # NOW task should be PENDING
        final_task = await task_center.get_task(task.id)
        assert final_task.status == TaskStatus.PENDING
    
    async def test_dependency_on_failed_task_blocks_indefinitely(self, task_center):
        """
        Task depending on FAILED task should remain WAITING_DEPENDENCY.
        
        Per Document 1: TaskCenter does not auto-fail dependent tasks.
        """
        # Create and fail dependency
        dep = await task_center.create_task(
            name="Failing Dep",
            description="Will fail",
            role="role"
        )
        await task_center.update_status(dep.id, TaskStatus.RUNNING)
        await task_center.fail_task(dep.id, "Intentional failure")
        
        # Create dependent task
        child = await task_center.create_task(
            name="Blocked Child",
            description="Blocked by failure",
            role="role",
            depends_on=[dep.id]
        )
        
        # Should be WAITING_DEPENDENCY
        assert child.status == TaskStatus.WAITING_DEPENDENCY
        
        # Should NOT auto-transition even though dependency is terminal
        # (This is by design - upper layers decide how to handle failures)