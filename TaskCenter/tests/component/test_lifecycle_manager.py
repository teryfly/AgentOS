"""
Component tests for LifecycleManager.
"""
import pytest
import uuid
from agent_os.common import TaskStatus, TaskResult, InvalidStatusTransitionError
from agent_os.task_center.lifecycle import LifecycleManager
from tests.utils.task_builder import TaskBuilder
from tests.utils.mock_event_bus import MockEventBus


@pytest.mark.asyncio
class TestLifecycleManager:
    """Test lifecycle coordination."""

    async def test_update_status_publishes_event(self, task_store, mock_event_bus: MockEventBus):
        """Should update status and publish event."""
        manager = LifecycleManager(task_store, mock_event_bus)

        task = TaskBuilder().with_status(TaskStatus.PENDING).build()
        await task_store.create(task)

        updated = await manager.update_status(task.id, TaskStatus.RUNNING)

        assert updated.status == TaskStatus.RUNNING
        assert len(mock_event_bus.published_events) == 1

    async def test_update_status_validates_transition(self, task_store, mock_event_bus: MockEventBus):
        """Should raise error on illegal transition."""
        manager = LifecycleManager(task_store, mock_event_bus)

        task = TaskBuilder().with_status(TaskStatus.PENDING).build()
        await task_store.create(task)

        with pytest.raises(InvalidStatusTransitionError):
            await manager.update_status(task.id, TaskStatus.COMPLETED)

    async def test_complete_task_unblocks_dependents(self, task_store, mock_event_bus: MockEventBus):
        """Should unblock tasks waiting on this dependency."""
        manager = LifecycleManager(task_store, mock_event_bus)

        parent_id = str(uuid.uuid4())
        child_id = str(uuid.uuid4())

        parent = TaskBuilder().with_id(parent_id).with_status(TaskStatus.RUNNING).build()
        child = (
            TaskBuilder()
            .with_id(child_id)
            .with_depends_on(parent_id)
            .with_status(TaskStatus.WAITING_DEPENDENCY)
            .build()
        )

        await task_store.create(parent)
        await task_store.create(child)
        await task_store.add_child(parent_id, child_id)

        result = TaskResult(success=True, data="done", error=None)
        await manager.complete_task(parent_id, result)

        child_updated = await task_store.get(child_id)
        assert child_updated.status == TaskStatus.PENDING

    async def test_fail_task_sets_error_result(self, task_store, mock_event_bus: MockEventBus):
        """Should set failure result."""
        manager = LifecycleManager(task_store, mock_event_bus)

        task = TaskBuilder().with_status(TaskStatus.RUNNING).build()
        await task_store.create(task)

        await manager.fail_task(task.id, "Test error")

        updated = await task_store.get(task.id)
        assert updated.status == TaskStatus.FAILED
        assert updated.result.success is False
        assert updated.result.error == "Test error"

    async def test_resume_task_transitions_to_running(self, task_store, mock_event_bus: MockEventBus):
        """Should resume from WAITING_INPUT."""
        manager = LifecycleManager(task_store, mock_event_bus)

        task = TaskBuilder().with_status(TaskStatus.WAITING_INPUT).build()
        await task_store.create(task)

        await manager.resume_task(task.id, {"user_input": "test"})

        updated = await task_store.get(task.id)
        assert updated.status == TaskStatus.RUNNING