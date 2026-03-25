"""
Abstract storage interface for MemoryCenter.

This module defines the contract that all storage implementations must follow.
All methods are async to support the system-wide async architecture.
"""

from abc import ABC, abstractmethod
from typing import Optional

from agent_os.common import MemoryItem, MemoryType


class MemoryStorage(ABC):
    """
    Abstract base class for memory storage implementations.
    
    All storage implementations must provide async methods for:
    - Saving memories (single and batch)
    - Querying by task_id with optional type filtering
    - Keyword search (with optional task_id scoping)
    - Deleting memories
    """

    @abstractmethod
    async def save(self, memory: MemoryItem) -> None:
        """
        Persist a single MemoryItem.
        
        Args:
            memory: The memory item to persist
            
        Raises:
            Exception: Storage-specific errors (should be caught by facade)
        """
        raise NotImplementedError

    @abstractmethod
    async def save_batch(self, memories: list[MemoryItem]) -> None:
        """
        Persist multiple MemoryItems in a batch operation.
        
        This is a best-effort operation - partial failures should be logged
        but not propagate exceptions.
        
        Args:
            memories: List of memory items to persist
            
        Raises:
            Exception: Storage-specific errors (should be caught by facade)
        """
        raise NotImplementedError

    @abstractmethod
    async def query_by_task(
        self,
        task_id: str,
        types: Optional[list[MemoryType]] = None
    ) -> list[MemoryItem]:
        """
        Retrieve memories associated with a task.
        
        Args:
            task_id: The task identifier
            types: Optional list of memory types to filter by.
                   If None, returns all types.
                   
        Returns:
            List of MemoryItem instances, ordered by created_at DESC
            
        Raises:
            Exception: Storage-specific errors (should be caught by facade)
        """
        raise NotImplementedError

    @abstractmethod
    async def search_keyword(
        self,
        query: str,
        task_id: Optional[str] = None,
        top_k: int = 5
    ) -> list[MemoryItem]:
        """
        Full-text search in memory content.
        
        Args:
            query: Search query string
            task_id: Optional task scope. If None, performs cross-task search.
            top_k: Maximum number of results to return
            
        Returns:
            List of MemoryItem instances, ordered by relevance (DESC)
            
        Raises:
            Exception: Storage-specific errors (should be caught by facade)
            
        Note:
            When task_id=None, this performs a global cross-task search,
            which is used by downstream tasks (e.g., result_router) to
            retrieve LONG memories from upstream tasks.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, memory_id: str) -> None:
        """
        Delete a specific memory by its ID.
        
        Args:
            memory_id: The unique identifier of the memory to delete
            
        Raises:
            Exception: Storage-specific errors (should be caught by facade)
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_by_task(
        self,
        task_id: str,
        types: Optional[list[MemoryType]] = None
    ) -> None:
        """
        Delete all memories for a task, optionally filtered by type.
        
        Args:
            task_id: The task identifier
            types: Optional list of memory types to delete.
                   If None, deletes all types.
                   
        Raises:
            Exception: Storage-specific errors (should be caught by facade)
            
        Note:
            Typically used to clean up SHORT memories after task completion.
            LONG memories are usually retained for cross-task retrieval.
        """
        raise NotImplementedError