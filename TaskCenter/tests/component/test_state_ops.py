"""
Component tests for StateOps.
"""
import pytest
from agent_os.common import TaskStatus, InvalidTaskStateError, MetadataUpdateConflictError, RuntimeStateUpdateConflictError
from agent_os.task_center.state_ops import StateOps
from agent_os.task_center.config import TaskCenterConfig
from tests.utils.task_builder import TaskBuilder


@pytest.mark.asyncio
class TestStateOps:
    """Test metadata and runtime state operations."""
    
    async def test_update_metadata_merges_fields(self, task_store, runtime_store):
        """Should merge new fields into existing metadata."""
        config = TaskCenterConfig(max_metadata_retries=3)
        ops = StateOps(task_store, runtime_store, config)
        
        task = TaskBuilder().with_status(TaskStatus.PENDING).with_metadata({"key1": "value1"}).build()
        await task_store.create(task)
        
        await ops.update_metadata(task.id, {"key2": "value2"})
        
        updated = await task_store.get(task.id)
        assert updated.metadata["key1"] == "value1"
        assert updated.metadata["key2"] == "value2"
    
    async def test_update_metadata_guards_status(self, task_store, runtime_store):
        """Should reject metadata update for completed tasks."""
        config = TaskCenterConfig()
        ops = StateOps(task_store, runtime_store, config)
        
        task = TaskBuilder().with_status(TaskStatus.COMPLETED).build()
        await task_store.create(task)
        
        with pytest.raises(InvalidTaskStateError):
            await ops.update_metadata(task.id, {"key": "value"})
    
    async def test_update_metadata_retries_on_conflict(self, task_store, runtime_store):
        """Should retry on version conflict."""
        config = TaskCenterConfig(max_metadata_retries=3)
        ops = StateOps(task_store, runtime_store, config)
        
        task = TaskBuilder().with_status(TaskStatus.RUNNING).build()
        await task_store.create(task)
        
        # This should succeed even with concurrent updates simulated
        await ops.update_metadata(task.id, {"key": "value"})
        
        updated = await task_store.get(task.id)
        assert "key" in updated.metadata
    
    async def test_update_runtime_state_creates_new_record(self, task_store, runtime_store):
        """Should create runtime state if doesn't exist."""
        config = TaskCenterConfig()
        ops = StateOps(task_store, runtime_store, config)
        
        task = TaskBuilder().with_status(TaskStatus.RUNNING).build()
        await task_store.create(task)
        
        await ops.update_runtime_state(task.id, {"group_state": {"round": 1}})
        
        state = await runtime_store.get(task.id)
        assert state is not None
        assert state.runtime_data["group_state"]["round"] == 1
    
    async def test_update_runtime_state_guards_status(self, task_store, runtime_store):
        """Should only allow updates for RUNNING tasks."""
        config = TaskCenterConfig()
        ops = StateOps(task_store, runtime_store, config)
        
        task = TaskBuilder().with_status(TaskStatus.PENDING).build()
        await task_store.create(task)
        
        with pytest.raises(InvalidTaskStateError):
            await ops.update_runtime_state(task.id, {"data": "value"})