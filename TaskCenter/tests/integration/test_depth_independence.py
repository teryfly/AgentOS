"""
Integration tests for depth/control boundary and metadata/runtime-state separation.

These tests align with:
- Document 0: depth vs step_depth independence
- Document 1: metadata/runtime_state separation and metadata state guard
"""
import pytest
from agent_os.common import TaskStatus, TaskResult, InvalidTaskStateError
from tests.utils.task_builder import BatchItemBuilder


@pytest.mark.asyncio
class TestDepthIndependence:
    """
    Verify DAG depth (max_depth) and runtime execution step concept are independent.
    """

    async def test_dag_depth_does_not_limit_execution_steps(self, task_center):
        """
        TaskCenter max_depth constrains only DAG nesting.
        It does not enforce AgentRuntime's max_step_depth.
        """
        items = [
            BatchItemBuilder().with_ref_id("task1").build(),
            BatchItemBuilder().with_ref_id("task2").depends_on_refs("task1").build(),
            BatchItemBuilder().with_ref_id("task3").depends_on_refs("task2").build(),
            BatchItemBuilder().with_ref_id("task4").depends_on_refs("task3").build(),
        ]

        result = await task_center.create_task_batch(items)
        assert len(result) == 4

        # Unblock chain legally through completion flow
        t1 = result["task1"]
        t2 = result["task2"]
        t3 = result["task3"]
        t4 = result["task4"]

        # Execute t1: PENDING → RUNNING → COMPLETED
        await task_center.update_status(t1.id, TaskStatus.RUNNING)
        await task_center.complete_task(t1.id, TaskResult(success=True, data="ok", error=None))

        # t2 should now be PENDING (unblocked)
        latest_t2 = await task_center.get_task(t2.id)
        assert latest_t2.status == TaskStatus.PENDING

        # Execute t2: PENDING → RUNNING → COMPLETED
        await task_center.update_status(t2.id, TaskStatus.RUNNING)
        await task_center.complete_task(t2.id, TaskResult(success=True, data="ok", error=None))

        # t3 should now be PENDING (unblocked)
        latest_t3 = await task_center.get_task(t3.id)
        assert latest_t3.status == TaskStatus.PENDING

        # Execute t3: PENDING → RUNNING → COMPLETED
        await task_center.update_status(t3.id, TaskStatus.RUNNING)
        await task_center.complete_task(t3.id, TaskResult(success=True, data="ok", error=None))

        # t4 should now be PENDING (unblocked)
        latest_t4 = await task_center.get_task(t4.id)
        assert latest_t4.status == TaskStatus.PENDING

        # Execute t4 with many metadata updates (simulating execution steps)
        await task_center.update_status(t4.id, TaskStatus.RUNNING)

        # Simulate many runtime loop updates via metadata API (allowed in RUNNING).
        # This validates TaskCenter does not impose execution-step limits.
        for step in range(60):
            await task_center.update_task_metadata(t4.id, {f"step_{step}": step})

        final_task = await task_center.get_task(t4.id)
        assert final_task.metadata["step_59"] == 59


@pytest.mark.asyncio
class TestMetadataSemanticBoundary:
    """
    Verify metadata and runtime state are semantically separated.
    """

    async def test_metadata_should_not_contain_runtime_state(self, task_center):
        """
        Runtime mutable state should be persisted via runtime_state table,
        not task.metadata.
        """
        task = await task_center.create_task(
            name="Task",
            description="Test",
            role="role",
            metadata={"project_id": 42, "root_dir": "/tmp"},
        )

        await task_center.update_status(task.id, TaskStatus.RUNNING)

        await task_center.update_task_runtime_state(
            task.id,
            {"group_state": {"round": 1, "history": []}},
        )

        await task_center.update_task_metadata(task.id, {"max_retries": 3})

        updated_task = await task_center.get_task(task.id)
        runtime_state = await task_center.get_task_runtime_state(task.id)

        assert updated_task.metadata["project_id"] == 42
        assert updated_task.metadata["max_retries"] == 3
        assert "group_state" not in updated_task.metadata

        assert runtime_state is not None
        assert runtime_state.runtime_data["group_state"]["round"] == 1

    async def test_metadata_update_forbidden_after_completion(self, task_center):
        """
        Metadata update is only allowed in PENDING/RUNNING.
        """
        task = await task_center.create_task(
            name="Task",
            description="Test",
            role="role",
        )

        await task_center.update_status(task.id, TaskStatus.RUNNING)
        await task_center.complete_task(task.id, TaskResult(success=True, data="done", error=None))

        with pytest.raises(InvalidTaskStateError):
            await task_center.update_task_metadata(task.id, {"key": "value"})