"""
Terminal lifecycle operations: complete, fail, resume.

Handles result persistence, dependency unblocking, and user input resumption.
"""
import logging
from typing import Any
from agent_os.common import (
    TaskResult,
    TaskStatus,
    TaskCompleted,
    TaskFailed,
    TaskResumed,
    InvalidStatusTransitionError,
)
from agent_os.common.interfaces import EventBus
from ..state_machine import validate_transition
from ..storage.interfaces import VersionConflict

logger = logging.getLogger(__name__)


class TerminalTransitions:
    """
    Handles terminal lifecycle transitions.
    """

    def __init__(self, task_store, event_bus: EventBus, unblock_handler):
        """
        Args:
            task_store: TaskStore instance
            event_bus: EventBus for publishing events
            unblock_handler: UnblockHandler instance
        """
        self._task_store = task_store
        self._event_bus = event_bus
        self._unblock_handler = unblock_handler

    async def complete_task(self, task_id: str, result: TaskResult) -> None:
        """
        Mark task as completed and unblock dependents.
        """
        task = await self._task_store.get(task_id)
        validate_transition(task.status, TaskStatus.COMPLETED)

        task.status = TaskStatus.COMPLETED
        task.result = result
        updated = await self._task_store.update(task)

        await self._event_bus.publish(TaskCompleted(task_id=updated.id, result=result))
        logger.info(f"[TaskCenter | TerminalTransitions | complete_task] Completed task {task_id}")

        for child_id in updated.children:
            try:
                child = await self._task_store.get(child_id)
                await self._unblock_handler.try_unblock(child)
            except Exception as e:
                logger.warning(
                    f"[TaskCenter | TerminalTransitions | complete_task] "
                    f"Failed to unblock child {child_id}: {e}"
                )

    async def fail_task(self, task_id: str, error: str) -> None:
        """
        Mark task as failed.
        """
        task = await self._task_store.get(task_id)
        validate_transition(task.status, TaskStatus.FAILED)

        task.status = TaskStatus.FAILED
        task.result = TaskResult(success=False, data=None, error=error)
        updated = await self._task_store.update(task)

        await self._event_bus.publish(TaskFailed(task_id=updated.id, error=error))
        logger.info(f"[TaskCenter | TerminalTransitions | fail_task] Failed task {task_id}: {error}")

    async def resume_task(self, task_id: str, input_data: Any) -> None:
        """
        Resume task from WAITING_INPUT with user input.

        Concurrency behavior:
        - First concurrent caller succeeds
        - Later callers get InvalidStatusTransitionError
        """
        task = await self._task_store.get(task_id)

        if task.status != TaskStatus.WAITING_INPUT:
            raise InvalidStatusTransitionError(
                f"Cannot resume task {task_id}: status is {task.status.value}, expected WAITING_INPUT"
            )

        try:
            updated = await self._task_store.cas_update_status(
                task_id=task_id,
                expected_version=task.version,
                new_status=TaskStatus.RUNNING,
            )
        except VersionConflict as e:
            # Concurrency-safe normalization:
            # CAS conflict here means another concurrent resume already changed state.
            raise InvalidStatusTransitionError(
                f"Cannot resume task {task_id}: concurrent resume detected"
            ) from e

        await self._event_bus.publish(TaskResumed(task_id=updated.id, input_data=input_data))
        logger.info(f"[TaskCenter | TerminalTransitions | resume_task] Resumed task {task_id}")