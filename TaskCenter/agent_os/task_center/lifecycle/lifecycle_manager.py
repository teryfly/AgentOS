"""
Lifecycle coordinator.

Delegates operations to specialized transition handlers.
"""
import logging
from typing import Any
from agent_os.common import Task, TaskResult, TaskStatus
from agent_os.common.interfaces import EventBus
from .status_transitions import StatusTransitions
from .terminal_transitions import TerminalTransitions
from .unblock_handler import UnblockHandler

logger = logging.getLogger(__name__)


class LifecycleManager:
    """
    Coordinates all task lifecycle operations.
    """
    
    def __init__(self, task_store, event_bus: EventBus):
        """
        Args:
            task_store: TaskStore instance
            event_bus: EventBus for event publishing
        """
        self._unblock_handler = UnblockHandler(task_store, event_bus)
        self._status_transitions = StatusTransitions(task_store, event_bus)
        self._terminal_transitions = TerminalTransitions(
            task_store, event_bus, self._unblock_handler
        )
    
    async def update_status(self, task_id: str, status: TaskStatus) -> Task:
        """Delegate status update."""
        return await self._status_transitions.update_status(task_id, status)
    
    async def complete_task(self, task_id: str, result: TaskResult) -> None:
        """Delegate task completion."""
        await self._terminal_transitions.complete_task(task_id, result)
    
    async def fail_task(self, task_id: str, error: str) -> None:
        """Delegate task failure."""
        await self._terminal_transitions.fail_task(task_id, error)
    
    async def resume_task(self, task_id: str, input_data: Any) -> None:
        """Delegate task resumption."""
        await self._terminal_transitions.resume_task(task_id, input_data)