"""
Unit tests for BatchValidator.
"""
import pytest
from agent_os.common import DuplicateRefIdError, DependencyNotFoundError
from agent_os.task_center.batch.batch_validator import BatchValidator
from tests.utils.task_builder import BatchItemBuilder


class MockTaskStore:
    """Mock task store for testing."""
    
    def __init__(self, existing_ids: set):
        self.existing_ids = existing_ids
    
    async def get(self, task_id: str):
        if task_id not in self.existing_ids:
            raise DependencyNotFoundError(f"Task {task_id} not found")
        return None  # Don't need actual task


class TestBatchValidator:
    """Test batch validation logic."""
    
    def test_check_ref_uniqueness_passes_with_unique_refs(self):
        """Unique ref_ids should pass validation."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").build(),
            BatchItemBuilder().with_ref_id("task3").build()
        ]
        
        # Should not raise
        BatchValidator.check_ref_uniqueness(items)
    
    def test_check_ref_uniqueness_raises_on_duplicate(self):
        """Duplicate ref_ids should raise error."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").build(),
            BatchItemBuilder().with_ref_id("task1").build()  # Duplicate
        ]
        
        with pytest.raises(DuplicateRefIdError):
            BatchValidator.check_ref_uniqueness(items)
    
    @pytest.mark.asyncio
    async def test_check_external_deps_exist_passes(self):
        """All existing dependencies should pass."""
        mock_store = MockTaskStore({"id-001", "id-002"})
        validator = BatchValidator(mock_store)
        
        external_deps = {"id-001", "id-002"}
        
        # Should not raise
        await validator.check_external_deps_exist(external_deps)
    
    @pytest.mark.asyncio
    async def test_check_external_deps_exist_raises_on_missing(self):
        """Missing dependency should raise error."""
        mock_store = MockTaskStore({"id-001"})
        validator = BatchValidator(mock_store)
        
        external_deps = {"id-001", "id-002"}  # id-002 doesn't exist
        
        with pytest.raises(DependencyNotFoundError):
            await validator.check_external_deps_exist(external_deps)