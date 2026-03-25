"""
Component tests for PgRuntimeStateStore.
"""
import pytest
import uuid
from agent_os.task_center.storage import PgRuntimeStateStore
from agent_os.task_center.storage.interfaces import VersionConflict


@pytest.mark.asyncio
class TestPgRuntimeStateStore:
    """Test PostgreSQL runtime state store operations."""

    async def test_get_nonexistent_returns_none(self, runtime_store: PgRuntimeStateStore):
        """Should return None for non-existent task."""
        result = await runtime_store.get(str(uuid.uuid4()))
        assert result is None

    async def test_upsert_creates_new_record(self, runtime_store: PgRuntimeStateStore):
        """Should create new runtime state record."""
        task_id = str(uuid.uuid4())
        state = await runtime_store.upsert(
            task_id,
            {"group_state": {"round": 1}},
            expected_version=None
        )

        assert state.task_id == task_id
        assert state.runtime_data["group_state"]["round"] == 1
        assert state.version == 0

    async def test_upsert_merges_existing_data(self, runtime_store: PgRuntimeStateStore):
        """Should merge new data into existing record."""
        task_id = str(uuid.uuid4())

        await runtime_store.upsert(task_id, {"key1": "value1"}, expected_version=None)
        updated = await runtime_store.upsert(task_id, {"key2": "value2"}, expected_version=None)

        assert updated.runtime_data["key1"] == "value1"
        assert updated.runtime_data["key2"] == "value2"
        assert updated.version == 1

    async def test_upsert_with_cas_success(self, runtime_store: PgRuntimeStateStore):
        """Should update with version check."""
        task_id = str(uuid.uuid4())
        state = await runtime_store.upsert(task_id, {"data": "v1"}, expected_version=None)

        updated = await runtime_store.upsert(
            task_id,
            {"data": "v2"},
            expected_version=state.version
        )

        assert updated.runtime_data["data"] == "v2"
        assert updated.version == state.version + 1

    async def test_upsert_with_cas_conflict_raises_error(self, runtime_store: PgRuntimeStateStore):
        """Should raise VersionConflict on mismatch."""
        task_id = str(uuid.uuid4())

        await runtime_store.upsert(task_id, {"data": "v1"}, expected_version=None)
        await runtime_store.upsert(task_id, {"data": "v2"}, expected_version=0)

        with pytest.raises(VersionConflict):
            await runtime_store.upsert(task_id, {"data": "v3"}, expected_version=0)

    async def test_delete_removes_record(self, runtime_store: PgRuntimeStateStore):
        """Should delete runtime state record."""
        task_id = str(uuid.uuid4())

        await runtime_store.upsert(task_id, {"data": "value"}, expected_version=None)
        await runtime_store.delete(task_id)

        result = await runtime_store.get(task_id)
        assert result is None

    async def test_delete_idempotent(self, runtime_store: PgRuntimeStateStore):
        """Should not raise error if record doesn't exist."""
        await runtime_store.delete(str(uuid.uuid4()))