"""
Component tests for PgTaskStore with real PostgreSQL.
"""
import pytest
import uuid
from agent_os.common import TaskStatus, TaskNotFoundError
from agent_os.task_center.storage import PgTaskStore
from agent_os.task_center.storage.interfaces import VersionConflict
from tests.utils.task_builder import TaskBuilder


@pytest.mark.asyncio
class TestPgTaskStore:
    """Test PostgreSQL task store operations."""

    async def test_create_task(self, task_store: PgTaskStore):
        """Should persist task with all fields."""
        task = TaskBuilder().with_name("Create Test").build()
        original_id = task.id

        created = await task_store.create(task)

        assert created.id == original_id
        assert created.name == "Create Test"
        assert created.version == 0

    async def test_get_task_exists(self, task_store: PgTaskStore):
        """Should retrieve existing task."""
        task = TaskBuilder().build()
        await task_store.create(task)

        retrieved = await task_store.get(task.id)

        assert retrieved.id == task.id
        assert retrieved.name == task.name

    async def test_get_task_not_found_raises_error(self, task_store: PgTaskStore):
        """Should raise TaskNotFoundError for non-existent ID."""
        with pytest.raises(TaskNotFoundError):
            await task_store.get(str(uuid.uuid4()))

    async def test_update_task_cas_success(self, task_store: PgTaskStore):
        """Should update task with version increment."""
        task = TaskBuilder().with_status(TaskStatus.PENDING).build()
        created = await task_store.create(task)

        created.status = TaskStatus.RUNNING
        updated = await task_store.update(created)

        assert updated.status == TaskStatus.RUNNING
        assert updated.version == created.version + 1

    async def test_update_task_cas_conflict_raises_error(self, task_store: PgTaskStore):
        """Should raise VersionConflict on concurrent modification."""
        task = TaskBuilder().build()
        created = await task_store.create(task)

        created.status = TaskStatus.RUNNING
        await task_store.update(created)

        created.name = "Modified"
        with pytest.raises(VersionConflict):
            await task_store.update(created)

    async def test_list_by_status(self, task_store: PgTaskStore):
        """Should filter tasks by status."""
        task1 = TaskBuilder().with_status(TaskStatus.PENDING).build()
        task2 = TaskBuilder().with_status(TaskStatus.RUNNING).build()
        task3 = TaskBuilder().with_status(TaskStatus.PENDING).build()

        await task_store.create(task1)
        await task_store.create(task2)
        await task_store.create(task3)

        pending_tasks = await task_store.list_by(status=TaskStatus.PENDING)

        assert len(pending_tasks) == 2
        assert all(t.status == TaskStatus.PENDING for t in pending_tasks)

    async def test_get_runnable_returns_ready_tasks(self, task_store: PgTaskStore):
        """Should return PENDING tasks with completed dependencies."""
        dep = TaskBuilder().with_status(TaskStatus.COMPLETED).build()
        task = TaskBuilder().with_depends_on(dep.id).with_status(TaskStatus.PENDING).build()

        await task_store.create(dep)
        await task_store.create(task)

        runnable = await task_store.get_runnable()

        assert len(runnable) == 1
        assert runnable[0].id == task.id

    async def test_add_child_updates_array(self, task_store: PgTaskStore):
        """Should append child_id to children array."""
        parent = TaskBuilder().build()
        child_id = str(uuid.uuid4())
        await task_store.create(parent)

        await task_store.add_child(parent.id, child_id)

        updated = await task_store.get(parent.id)
        assert child_id in updated.children

    async def test_cas_update_status_success(self, task_store: PgTaskStore):
        """Should atomically update status with version check."""
        task = TaskBuilder().with_status(TaskStatus.PENDING).build()
        created = await task_store.create(task)

        updated = await task_store.cas_update_status(
            created.id,
            created.version,
            TaskStatus.RUNNING
        )

        assert updated.status == TaskStatus.RUNNING
        assert updated.version == created.version + 1

    async def test_batch_create_in_tx_success(self, task_store: PgTaskStore, db_pool):
        """Should create all tasks in transaction."""
        tasks = [TaskBuilder().with_name(f"Batch {i}").build() for i in range(3)]

        async def create_batch(conn):
            return await task_store.batch_create_in_tx(conn, tasks)

        created = await db_pool.execute_in_transaction(create_batch)

        assert len(created) == 3
        for task in created:
            retrieved = await task_store.get(task.id)
            assert retrieved is not None