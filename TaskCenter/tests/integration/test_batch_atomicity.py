"""
Integration test: Batch creation atomicity.
"""
import pytest
from agent_os.common import TaskBatchItem, DependencyNotFoundError
from tests.utils.task_builder import BatchItemBuilder


@pytest.mark.asyncio
class TestBatchAtomicity:
    """Test atomic batch operations."""
    
    async def test_successful_batch_creates_all_tasks(self, task_center):
        """Successful batch should create all tasks."""
        items = [
            BatchItemBuilder().with_ref_id("task1").with_name("Task 1").build(),
            BatchItemBuilder().with_ref_id("task2").with_name("Task 2").build(),
            BatchItemBuilder().with_ref_id("task3").with_name("Task 3").build()
        ]
        
        result = await task_center.create_task_batch(items)
        
        assert len(result) == 3
        
        # All tasks should be persisted
        for ref_id, task in result.items():
            retrieved = await task_center.get_task(task.id)
            assert retrieved.id == task.id
    
    async def test_batch_with_invalid_dependency_rolls_back(self, task_center):
        """Batch with invalid external dependency should rollback."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder()
                .with_ref_id("task2")
                .depends_on_ids("non-existent-id")  # Invalid dependency
                .build()
        ]
        
        with pytest.raises(DependencyNotFoundError):
            await task_center.create_task_batch(items)
        
        # No tasks should be created
        all_tasks = await task_center.list_tasks()
        assert len(all_tasks) == 0
    
    async def test_batch_with_internal_dependencies(self, task_center):
        """Batch with internal dependencies should resolve correctly."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build(),
            BatchItemBuilder().with_ref_id("task3").depends_on_refs("task1", "task2").build()
        ]
        
        result = await task_center.create_task_batch(items)
        
        # Verify dependency resolution
        task3 = result["task3"]
        task1_id = result["task1"].id
        task2_id = result["task2"].id
        
        assert task1_id in task3.depends_on
        assert task2_id in task3.depends_on