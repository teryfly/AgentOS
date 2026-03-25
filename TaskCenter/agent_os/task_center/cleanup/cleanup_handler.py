"""
Event-driven runtime state cleanup.

Subscribes to terminal task events and asynchronously deletes runtime state.
"""
import logging
from agent_os.common import TaskCompleted, TaskFailed
from agent_os.common.interfaces import EventBus

logger = logging.getLogger(__name__)


class CleanupHandler:
    """
    Manages automatic cleanup of runtime state on task completion.
    """
    
    def __init__(self, runtime_store, event_bus: EventBus):
        """
        Args:
            runtime_store: RuntimeStateStore instance
            event_bus: EventBus for subscribing to terminal events
        """
        self._runtime_store = runtime_store
        self._event_bus = event_bus
    
    async def initialize(self) -> None:
        """Subscribe to terminal task events."""
        self._event_bus.subscribe(TaskCompleted, self._on_task_terminal)
        self._event_bus.subscribe(TaskFailed, self._on_task_terminal)
        logger.info("[TaskCenter | CleanupHandler | initialize] Subscribed to terminal events")
    
    async def _on_task_terminal(self, event: TaskCompleted | TaskFailed) -> None:
        """
        Handle terminal event by deleting runtime state.
        
        Failures are logged as warnings but do not propagate.
        """
        try:
            await self._runtime_store.delete(event.task_id)
            logger.debug(f"[TaskCenter | CleanupHandler | _on_task_terminal] Cleaned up runtime state for {event.task_id}")
        except Exception as e:
            logger.warning(
                f"[TaskCenter | CleanupHandler | _on_task_terminal] "
                f"Failed to delete runtime state for {event.task_id}: {e}"
            )