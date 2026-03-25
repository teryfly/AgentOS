"""
Abstract storage interfaces for TaskCenter.

Defines contracts for task and runtime state persistence.
All implementations must be async and support CAS operations.
"""
from abc import ABC, abstractmethod
from typing import Any
from agent_os.common import Task, TaskStatus, TaskRuntimeState


class VersionConflict(Exception):
    """
    Internal exception indicating CAS version mismatch.
    
    Used by storage implementations to signal optimistic lock conflicts.
    Should not be exposed to external callers.
    """
    pass


class TaskStore(ABC):
    """
    Abstract interface for task persistence.
    
    All operations are atomic. CAS operations raise VersionConflict on mismatch.
    """
    
    @abstractmethod
    async def create(self, task: Task) -> Task:
        """
        Create new task.
        
        Args:
            task: Task to persist (id must be set)
            
        Returns:
            Created task with database-assigned timestamps
        """
        pass
    
    @abstractmethod
    async def get(self, task_id: str) -> Task:
        """
        Retrieve task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task instance
            
        Raises:
            TaskNotFoundError: Task does not exist
        """
        pass
    
    @abstractmethod
    async def list_by(
        self,
        status: TaskStatus | None = None,
        role: str | None = None
    ) -> list[Task]:
        """
        List tasks with optional filters.
        
        Args:
            status: Filter by status (None = no filter)
            role: Filter by role (None = no filter)
            
        Returns:
            List of matching tasks
        """
        pass
    
    @abstractmethod
    async def get_runnable(self) -> list[Task]:
        """
        Get all PENDING tasks with all dependencies COMPLETED.
        
        Returns:
            List of runnable tasks
        """
        pass
    
    @abstractmethod
    async def update(self, task: Task) -> Task:
        """
        Update task with CAS on version field.
        
        Args:
            task: Task with modified fields and current version
            
        Returns:
            Updated task with incremented version
            
        Raises:
            VersionConflict: Version mismatch (concurrent modification)
            TaskNotFoundError: Task does not exist
        """
        pass
    
    @abstractmethod
    async def add_child(self, task_id: str, child_id: str) -> None:
        """
        Append child_id to task's children array.
        
        Args:
            task_id: Parent task ID
            child_id: Child task ID to append
            
        Raises:
            TaskNotFoundError: Parent task does not exist
        """
        pass
    
    @abstractmethod
    async def cas_update_status(
        self,
        task_id: str,
        expected_version: int,
        new_status: TaskStatus
    ) -> Task:
        """
        Compare-And-Swap status update.
        
        Args:
            task_id: Task to update
            expected_version: Expected current version
            new_status: Target status
            
        Returns:
            Updated task with incremented version
            
        Raises:
            VersionConflict: Version mismatch
            TaskNotFoundError: Task does not exist
        """
        pass
    
    @abstractmethod
    async def batch_create_in_tx(
        self,
        conn: Any,  # asyncpg.Connection
        tasks: list[Task]
    ) -> list[Task]:
        """
        Batch create tasks within existing transaction.
        
        Args:
            conn: Active database connection with open transaction
            tasks: Tasks to create
            
        Returns:
            Created tasks with assigned timestamps
        """
        pass


class RuntimeStateStore(ABC):
    """
    Abstract interface for runtime state persistence.
    
    Supports upsert with optional CAS for concurrent updates.
    """
    
    @abstractmethod
    async def get(self, task_id: str) -> TaskRuntimeState | None:
        """
        Retrieve runtime state for task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Runtime state or None if not exists
        """
        pass
    
    @abstractmethod
    async def upsert(
        self,
        task_id: str,
        runtime_patch: dict,
        expected_version: int | None = None
    ) -> TaskRuntimeState:
        """
        Insert or update runtime state with optional CAS.
        
        Args:
            task_id: Task identifier
            runtime_patch: Fields to merge into runtime_data
            expected_version: If provided, enforce version match (None = no check)
            
        Returns:
            Updated runtime state with incremented version
            
        Raises:
            VersionConflict: Version mismatch (only if expected_version provided)
        """
        pass
    
    @abstractmethod
    async def delete(self, task_id: str) -> None:
        """
        Delete runtime state (idempotent).
        
        Args:
            task_id: Task identifier
        """
        pass