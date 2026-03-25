"""
Dependency unblocking logic.

Checks if task dependencies are satisfied and transitions to PENDING.
"""
import logging
from agent_os.common import Task, TaskStatus, TaskUnblocked
from agent_os.common.interfaces import EventBus

logger = logging.getLogger(__name__)


class UnblockHandler:
    """
    Handles task unblocking when dependencies are satisfied.
    """
    
    def __init__(self, task_store, event_bus: EventBus):
        """
        Args:
            task_store: TaskStore instance
            event_bus: EventBus for publishing TaskUnblocked
        """
        self._task_store = task_store
        self._event_bus = event_bus
    
    async def try_unblock(self, task: Task) -> None:
        """
        Attempt to unblock task if dependencies satisfied.
        
        Args:
            task: Task to check (must have status = WAITING_DEPENDENCY)
        """
        if task.status != TaskStatus.WAITING_DEPENDENCY:
            return
        
        # Fetch all dependencies
        all_completed = True
        for dep_id in task.depends_on:
            try:
                dep_task = await self._task_store.get(dep_id)
                if dep_task.status != TaskStatus.COMPLETED:
                    all_completed = False
                    break
            except Exception as e:
                logger.warning(f"[TaskCenter | UnblockHandler | try_unblock] Failed to fetch dependency {dep_id}: {e}")
                all_completed = False
                break
        
        if all_completed:
            # CAS transition to PENDING
            try:
                updated = await self._task_store.cas_update_status(
                    task.id,
                    task.version,
                    TaskStatus.PENDING
                )
                await self._event_bus.publish(TaskUnblocked(task_id=updated.id))
                logger.info(f"[TaskCenter | UnblockHandler | try_unblock] Unblocked task {task.id}")
            except Exception as e:
                logger.debug(f"[TaskCenter | UnblockHandler | try_unblock] Failed to unblock {task.id}: {e}")