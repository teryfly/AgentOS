"""
Integration test: Circular dependency detection.
"""
import pytest
from agent_os.common import CircularDependencyError
from tests.utils.task_builder import BatchItemBuilder


@pytest.mark.asyncio
class TestCircularDependency:
    """Test cycle detection across creation paths."""

    async def test_single_create_has_no_false_positive_cycle(self, task_center):
        """
        Single create_task cannot express a brand-new cycle because task.id is generated internally.
        This test verifies no false-positive cycle detection in valid single-task creation.
        """
        task = await task_center.create_task(
            name="Task A",
            description="No cycle in single create",
            role="role"
        )
        assert task.id is not None

    async def test_cycle_in_batch_rejected(self, task_center):
        """Cycle within batch should be rejected."""
        items = [
            BatchItemBuilder().with_ref_id("task1").depends_on_refs("task2").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task3").build(),
            BatchItemBuilder().with_ref_id("task3").depends_on_refs("task1").build()
        ]

        with pytest.raises(CircularDependencyError):
            await task_center.create_task_batch(items)

    async def test_self_reference_rejected(self, task_center):
        """Self-reference should be rejected."""
        items = [
            BatchItemBuilder().with_ref_id("task1").depends_on_refs("task1").build()
        ]

        with pytest.raises(CircularDependencyError):
            await task_center.create_task_batch(items)

    async def test_diamond_dependency_allowed(self, task_center):
        """Diamond pattern is not a cycle."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build(),
            BatchItemBuilder().with_ref_id("task3").depends_on_refs("task1").build(),
            BatchItemBuilder().with_ref_id("task4").depends_on_refs("task2", "task3").build()
        ]

        result = await task_center.create_task_batch(items)
        assert len(result) == 4