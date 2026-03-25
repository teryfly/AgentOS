"""
Unit tests for RefResolver.
"""
import pytest
from agent_os.task_center.batch.ref_resolver import RefResolver
from tests.utils.task_builder import BatchItemBuilder


class TestRefResolver:
    """Test ref_id resolution logic."""
    
    def test_generate_id_map_creates_unique_ids(self):
        """Each ref_id should map to unique task_id."""
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").build(),
            BatchItemBuilder().with_ref_id("task3").build()
        ]
        
        id_map = RefResolver.generate_id_map(items)
        
        assert len(id_map) == 3
        assert "task1" in id_map
        assert "task2" in id_map
        assert "task3" in id_map
        
        # All IDs should be unique
        ids = list(id_map.values())
        assert len(ids) == len(set(ids))
    
    def test_resolve_dependencies_with_refs(self):
        """Should resolve ref-based dependencies to task_ids."""
        item = (
            BatchItemBuilder()
            .with_ref_id("task3")
            .depends_on_refs("task1", "task2")
            .build()
        )
        
        ref_to_id = {
            "task1": "id-001",
            "task2": "id-002",
            "task3": "id-003"
        }
        
        resolved = RefResolver.resolve_dependencies(item, ref_to_id)
        
        assert resolved == ["id-001", "id-002"]
    
    def test_resolve_dependencies_with_external_ids(self):
        """Should include external task_ids."""
        item = (
            BatchItemBuilder()
            .with_ref_id("task1")
            .depends_on_ids("external-id-1", "external-id-2")
            .build()
        )
        
        ref_to_id = {"task1": "id-001"}
        
        resolved = RefResolver.resolve_dependencies(item, ref_to_id)
        
        assert resolved == ["external-id-1", "external-id-2"]
    
    def test_resolve_dependencies_mixed(self):
        """Should handle both refs and external IDs."""
        item = (
            BatchItemBuilder()
            .with_ref_id("task2")
            .depends_on_refs("task1")
            .depends_on_ids("external-id")
            .build()
        )
        
        ref_to_id = {
            "task1": "id-001",
            "task2": "id-002"
        }
        
        resolved = RefResolver.resolve_dependencies(item, ref_to_id)
        
        assert "id-001" in resolved
        assert "external-id" in resolved