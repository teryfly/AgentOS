"""
Unit tests for TaskRowMapper serialization.
"""
import pytest
import json
from agent_os.common import Task, TaskStatus, TaskResult
from agent_os.task_center.storage.task_row_mapper import TaskRowMapper
from tests.utils.task_builder import TaskBuilder


class TestTaskRowMapper:
    """Test Task <-> database row conversion."""
    
    def test_to_row_converts_all_fields(self):
        """to_row should serialize all Task fields."""
        task = (
            TaskBuilder()
            .with_id("test-id")
            .with_name("Test Task")
            .with_role("test_role")
            .with_status(TaskStatus.RUNNING)
            .with_depends_on("dep-1", "dep-2")
            .with_metadata({"key": "value"})
            .with_result(True, {"output": "data"}, None)
            .build()
        )
        
        row = TaskRowMapper.to_row(task)
        
        assert row["id"] == "test-id"
        assert row["name"] == "Test Task"
        assert row["role"] == "test_role"
        assert row["status"] == "RUNNING"
        
        # JSONB fields serialized
        assert json.loads(row["depends_on"]) == ["dep-1", "dep-2"]
        assert json.loads(row["metadata"]) == {"key": "value"}
        assert json.loads(row["result"])["success"] is True
    
    def test_from_row_reconstructs_task(self):
        """from_row should reconstruct Task from database row."""
        row = {
            "id": "test-id",
            "name": "Test Task",
            "description": "Description",
            "role": "test_role",
            "status": "PENDING",
            "depends_on": json.dumps(["dep-1"]),
            "children": json.dumps([]),
            "result": None,
            "metadata": json.dumps({"project_id": 42}),
            "created_at": 1000,
            "updated_at": 2000,
            "version": 0
        }
        
        task = TaskRowMapper.from_row(row)
        
        assert task.id == "test-id"
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert task.depends_on == ["dep-1"]
        assert task.metadata == {"project_id": 42}
    
    def test_round_trip_preserves_data(self):
        """to_row followed by from_row should preserve all data."""
        original = (
            TaskBuilder()
            .with_name("Round Trip Test")
            .with_metadata({"key1": "value1", "key2": 123})
            .with_depends_on("dep-1", "dep-2")
            .build()
        )
        
        row = TaskRowMapper.to_row(original)
        reconstructed = TaskRowMapper.from_row(row)
        
        assert reconstructed.id == original.id
        assert reconstructed.name == original.name
        assert reconstructed.metadata == original.metadata
        assert reconstructed.depends_on == original.depends_on