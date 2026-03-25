"""
Component tests for BatchProcessor.
"""
import pytest
import uuid
from agent_os.common import TaskCreated
from agent_os.task_center.batch import BatchProcessor
from agent_os.task_center.graph import GraphValidator
from tests.utils.task_builder import BatchItemBuilder, TaskBuilder
from tests.utils.mock_event_bus import MockEventBus


@pytest.mark.asyncio
class TestBatchProcessor:
    """Test atomic batch creation."""

    async def test_process_batch_creates_all_tasks(self, task_store, mock_event_bus: MockEventBus, db_pool):
        """Should create all tasks atomically."""
        validator = GraphValidator(max_depth=5)
        processor = BatchProcessor(task_store, validator, mock_event_bus, db_pool)

        items = [
            BatchItemBuilder().with_ref_id("task1").with_name("Task 1").build(),
            BatchItemBuilder().with_ref_id("task2").with_name("Task 2").build()
        ]

        result = await processor.process_batch(items)

        assert len(result) == 2
        assert "task1" in result
        assert "task2" in result

        events = mock_event_bus.get_events_by_type(TaskCreated)
        assert len(events) == 2

    async def test_process_batch_resolves_internal_dependencies(self, task_store, mock_event_bus: MockEventBus, db_pool):
        """Should resolve depends_on_refs within batch."""
        validator = GraphValidator(max_depth=5)
        processor = BatchProcessor(task_store, validator, mock_event_bus, db_pool)

        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build()
        ]

        result = await processor.process_batch(items)

        task2 = result["task2"]
        task1 = result["task1"]
        assert task1.id in task2.depends_on

    async def test_process_batch_validates_duplicate_refs(self, task_store, mock_event_bus: MockEventBus, db_pool):
        """Should raise error on duplicate ref_ids."""
        from agent_os.common import DuplicateRefIdError

        validator = GraphValidator(max_depth=5)
        processor = BatchProcessor(task_store, validator, mock_event_bus, db_pool)

        items = [
            BatchItemBuilder().with_ref_id("duplicate").build(),
            BatchItemBuilder().with_ref_id("duplicate").build()
        ]

        with pytest.raises(DuplicateRefIdError):
            await processor.process_batch(items)

    async def test_process_batch_updates_parent_children(self, task_store, mock_event_bus: MockEventBus, db_pool):
        """Should update parent task's children array."""
        validator = GraphValidator(max_depth=5)
        processor = BatchProcessor(task_store, validator, mock_event_bus, db_pool)

        parent_id = str(uuid.uuid4())
        parent = TaskBuilder().with_id(parent_id).build()
        await task_store.create(parent)

        items = [BatchItemBuilder().with_ref_id("child1").build()]

        result = await processor.process_batch(items, parent_task_id=parent_id)

        updated_parent = await task_store.get(parent_id)
        child_id = result["child1"].id
        assert child_id in updated_parent.children