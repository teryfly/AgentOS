"""
Component tests for UnblockHandler.
"""
import pytest
import uuid
from agent_os.common import TaskStatus, TaskUnblocked
from agent_os.task_center.lifecycle import UnblockHandler
from tests.utils.task_builder import TaskBuilder
from tests.utils.mock_event_bus import MockEventBus


@pytest.mark.asyncio
class TestUnblockHandler:
    """Test dependency unblocking logic."""

    async def test_try_unblock_ignores_non_waiting_tasks(self, task_store, mock_event_bus: MockEventBus):
        """Should not process tasks not in WAITING_DEPENDENCY."""
        handler = UnblockHandler(task_store, mock_event_bus)

        task = TaskBuilder().with_status(TaskStatus.PENDING).build()

        await handler.try_unblock(task)
        assert len(mock_event_bus.published_events) == 0

    async def test_try_unblock_succeeds_when_all_deps_completed(self, task_store, mock_event_bus: MockEventBus):
        """Should transition to PENDING when dependencies satisfied."""
        handler = UnblockHandler(task_store, mock_event_bus)

        dep1_id = str(uuid.uuid4())
        dep2_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        dep1 = TaskBuilder().with_id(dep1_id).with_status(TaskStatus.COMPLETED).build()
        dep2 = TaskBuilder().with_id(dep2_id).with_status(TaskStatus.COMPLETED).build()
        await task_store.create(dep1)
        await task_store.create(dep2)

        task = (
            TaskBuilder()
            .with_id(task_id)
            .with_depends_on(dep1_id, dep2_id)
            .with_status(TaskStatus.WAITING_DEPENDENCY)
            .build()
        )
        await task_store.create(task)

        await handler.try_unblock(task)

        updated = await task_store.get(task_id)
        assert updated.status == TaskStatus.PENDING

        events = mock_event_bus.get_events_by_type(TaskUnblocked)
        assert len(events) == 1

    async def test_try_unblock_does_not_unblock_partial_completion(self, task_store, mock_event_bus: MockEventBus):
        """Should not unblock if some dependencies incomplete."""
        handler = UnblockHandler(task_store, mock_event_bus)

        dep1_id = str(uuid.uuid4())
        dep2_id = str(uuid.uuid4())

        dep1 = TaskBuilder().with_id(dep1_id).with_status(TaskStatus.COMPLETED).build()
        dep2 = TaskBuilder().with_id(dep2_id).with_status(TaskStatus.RUNNING).build()
        await task_store.create(dep1)
        await task_store.create(dep2)

        task = (
            TaskBuilder()
            .with_depends_on(dep1_id, dep2_id)
            .with_status(TaskStatus.WAITING_DEPENDENCY)
            .build()
        )
        await task_store.create(task)

        await handler.try_unblock(task)

        updated = await task_store.get(task.id)
        assert updated.status == TaskStatus.WAITING_DEPENDENCY