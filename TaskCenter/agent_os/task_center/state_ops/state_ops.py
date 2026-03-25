"""
Metadata and runtime state update operations.

Implements merge-update semantics with optimistic locking and retry.
"""
import logging
from agent_os.common import (
    TaskStatus,
    InvalidTaskStateError,
    MetadataUpdateConflictError,
    RuntimeStateUpdateConflictError,
)
from .retry_cas import retry_optimistic

logger = logging.getLogger(__name__)


class StateOps:
    """
    Manages task metadata and runtime state updates.
    """

    def __init__(self, task_store, runtime_store, config):
        self._task_store = task_store
        self._runtime_store = runtime_store
        self._config = config

    async def update_metadata(self, task_id: str, metadata_patch: dict) -> None:
        """
        Merge-update task metadata with retry.
        """
        task = await self._task_store.get(task_id)
        if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            raise InvalidTaskStateError(
                f"Cannot update metadata for task {task_id} in status {task.status.value}"
            )

        async def update_op():
            current = await self._task_store.get(task_id)
            new_metadata = {**current.metadata, **metadata_patch}
            current.metadata = new_metadata
            await self._task_store.update(current)

        await retry_optimistic(
            update_op,
            self._config.max_metadata_retries,
            MetadataUpdateConflictError
        )

        logger.info(f"[TaskCenter | StateOps | update_metadata] Updated metadata for {task_id}")

    async def update_runtime_state(self, task_id: str, runtime_patch: dict) -> None:
        """
        Merge-update runtime state with retry.
        """
        task = await self._task_store.get(task_id)
        if task.status != TaskStatus.RUNNING:
            raise InvalidTaskStateError(
                f"Cannot update runtime state for task {task_id} in status {task.status.value}"
            )

        async def update_op():
            current_state = await self._runtime_store.get(task_id)

            if current_state is None:
                # CAS create. In race, store raises VersionConflict and retry handles it.
                await self._runtime_store.upsert(task_id, runtime_patch, expected_version=0)
            else:
                await self._runtime_store.upsert(
                    task_id,
                    runtime_patch,
                    expected_version=current_state.version
                )

        await retry_optimistic(
            update_op,
            self._config.max_runtime_retries,
            RuntimeStateUpdateConflictError
        )

        logger.info(f"[TaskCenter | StateOps | update_runtime_state] Updated runtime state for {task_id}")