"""
Non-terminal status transitions with event publishing.

Handles RUNNING, WAITING_INPUT, WAITING_DEPENDENCY transitions.
"""
import logging
from agent_os.common import Task, TaskStatus, TaskStarted, TaskWaitingInput, TaskWaitingDependency
from agent_os.common.interfaces import EventBus
from ..state_machine import validate_transition

logger = logging.getLogger(__name__)


# Map status to event class
EVENT_MAP = {
    TaskStatus.RUNNING: TaskStarted,
    TaskStatus.WAITING_INPUT: TaskWaitingInput,
    TaskStatus.WAITING_DEPENDENCY: TaskWaitingDependency
}


class StatusTransitions:
    """
    Handles non-terminal status updates.
    """
    
    def __init__(self, task_store, event_bus: EventBus):
        """
        Args:
            task_store: TaskStore instance
            event_bus: EventBus for publishing events
        """
        self._task_store = task_store
        self._event_bus = event_bus
    
    async def update_status(self, task_id: str, new_status: TaskStatus) -> Task:
        """
        Update task status with validation and event publishing.
        
        Args:
            task_id: Task to update
            new_status: Target status
            
        Returns:
            Updated task
            
        Raises:
            InvalidStatusTransitionError: Illegal transition
            TaskNotFoundError: Task not found
        """
        # Fetch current task
        task = await self._task_store.get(task_id)
        
        # Validate transition
        validate_transition(task.status, new_status)
        
        # CAS update
        updated = await self._task_store.cas_update_status(task_id, task.version, new_status)
        
        # Publish event if mapped
        event_class = EVENT_MAP.get(new_status)
        if event_class:
            await self._event_bus.publish(event_class(task_id=updated.id))
        
        logger.info(f"[TaskCenter | StatusTransitions | update_status] {task_id} -> {new_status.value}")
        return updated