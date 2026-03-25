"""
Integration test: Combined depth and cycle validation.
"""
import pytest
from agent_os.common import MaxDepthExceededError, CircularDependencyError
from tests.utils.task_builder import BatchItemBuilder


@pytest.mark.asyncio
class TestGraphValidationIntegration:
    """Test depth and cycle validation together."""
    
    async def test_deep_chain_within_limit_succeeds(self, task_center):
        """Chain within max_depth should succeed."""
        # Config has max_depth=5, create chain of 4
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build(),
            BatchItemBuilder().with_ref_id("task3").depends_on_refs("task2").build(),
            BatchItemBuilder().with_ref_id("task4").depends_on_refs("task3").build()
        ]
        
        # Should succeed
        result = await task_center.create_task_batch(items)
        assert len(result) == 4
    
    async def test_deep_chain_exceeding_limit_rejected(self, task_center):
        """Chain exceeding max_depth should be rejected."""
        # Config has max_depth=5, try to create chain of 6
        items = [BatchItemBuilder().with_ref_id(f"task{i}").build() for i in range(1, 2)]
        for i in range(2, 8):
            items.append(
                BatchItemBuilder().with_ref_id(f"task{i}").depends_on_refs(f"task{i-1}").build()
            )
        
        with pytest.raises(MaxDepthExceededError):
            await task_center.create_task_batch(items)
    
    async def test_cycle_detected_before_depth_check(self, task_center):
        """Cycle should be detected even if depth is valid."""
        items = [
            BatchItemBuilder().with_ref_id("task1").depends_on_refs("task2").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build()
        ]
        
        # Cycle should be detected first
        with pytest.raises(CircularDependencyError):
            await task_center.create_task_batch(items)