"""
Context assembly algorithm for building MemoryContext.

This module contains pure functions for:
- Fetching memories from storage
- Deduplication across sources
- Priority sorting
- Truncation to max_items_per_context

All functions are stateless and delegate I/O to the storage layer.
"""

import logging
from typing import Optional

from agent_os.common import MemoryConfig, MemoryContext, MemoryItem, MemoryType

from .storage.base import MemoryStorage

logger = logging.getLogger(__name__)


async def assemble_context(
    storage: MemoryStorage,
    config: MemoryConfig,
    task_id: str,
    include_shared: bool,
    query: Optional[str],
) -> MemoryContext:
    """
    Assemble memory context for a task.
    
    Algorithm:
      1. Fetch SHORT memories (task-scoped, ordered by created_at DESC)
      2. If include_shared: Fetch SHARED memories (global, ordered by created_at DESC)
      3. If query and keyword_search_enabled: Fetch search results (task-scoped)
      4. Deduplicate by memory_id (priority: SHORT > SHARED > search results)
      5. Priority sort: SHORT (newest first) → SHARED (newest first) → search (relevance)
      6. Truncate to config.max_items_per_context
      7. Return MemoryContext(task_id, items, truncated=bool)
      
    Args:
        storage: Storage implementation to fetch data from
        config: Memory configuration including max items and search settings
        task_id: Task identifier to scope memories
        include_shared: Whether to include SHARED type memories
        query: Optional search query for keyword search (task-scoped)
        
    Returns:
        MemoryContext with assembled and truncated memory items
        
    Note:
        This is a pure algorithm that delegates all I/O to storage.
        Failures in storage operations propagate up to be caught by the facade.
    """
    # Step 1: Fetch SHORT memories (task-scoped)
    short_memories = await storage.query_by_task(task_id, [MemoryType.SHORT])
    
    # Step 2: Fetch SHARED memories (if requested)
    shared_memories: list[MemoryItem] = []
    if include_shared:
        # SHARED memories are global, but we query by task_id for consistency
        # Note: In practice, SHARED memories may not be scoped to a task
        # This is a design choice that can be revisited
        shared_memories = await storage.query_by_task(task_id, [MemoryType.SHARED])
    
    # Step 3: Fetch search results (task-scoped)
    search_results: list[MemoryItem] = []
    if query and config.keyword_search_enabled:
        search_results = await storage.search_keyword(query, task_id, top_k=10)
    
    # Step 4: Deduplicate by memory_id
    deduped = _deduplicate_memories(short_memories, shared_memories, search_results)
    
    # Step 5: Priority sort
    sorted_memories = _priority_sort(deduped)
    
    # Step 6: Truncate to max_items_per_context
    truncated_items, was_truncated = _truncate(
        sorted_memories,
        config.max_items_per_context
    )
    
    return MemoryContext(
        task_id=task_id,
        items=truncated_items,
        truncated=was_truncated,
    )


def _deduplicate_memories(
    short: list[MemoryItem],
    shared: list[MemoryItem],
    search: list[MemoryItem],
) -> list[MemoryItem]:
    """
    Remove duplicate memories by ID across all sources.
    
    Priority order (first occurrence wins):
      1. SHORT memories
      2. SHARED memories
      3. Search results
      
    Args:
        short: SHORT type memories from task
        shared: SHARED type memories
        search: Keyword search results
        
    Returns:
        List of unique MemoryItem instances preserving priority order
        
    Note:
        Search results may overlap with SHORT/SHARED memories.
        We keep the higher-priority version and discard duplicates.
    """
    seen_ids: set[str] = set()
    result: list[MemoryItem] = []
    
    # Priority 1: SHORT memories
    for item in short:
        if item.id not in seen_ids:
            result.append(item)
            seen_ids.add(item.id)
    
    # Priority 2: SHARED memories
    for item in shared:
        if item.id not in seen_ids:
            result.append(item)
            seen_ids.add(item.id)
    
    # Priority 3: Search results
    for item in search:
        if item.id not in seen_ids:
            result.append(item)
            seen_ids.add(item.id)
    
    return result


def _priority_sort(memories: list[MemoryItem]) -> list[MemoryItem]:
    """
    Sort memories by type priority and recency.
    
    Sort key: (type_priority, -created_at)
      - Type priority: SHORT=0, SHARED=1, LONG=2
      - Within same type: newest first (created_at DESC)
      
    Args:
        memories: List of deduplicated MemoryItem instances
        
    Returns:
        Sorted list with SHORT memories first (newest first),
        then SHARED (newest first), then LONG (newest first)
        
    Note:
        LONG memories typically only appear from search results,
        as direct queries filter by type.
    """
    type_priority = {
        MemoryType.SHORT: 0,
        MemoryType.SHARED: 1,
        MemoryType.LONG: 2,
    }
    
    return sorted(
        memories,
        key=lambda m: (type_priority.get(m.type, 99), -m.created_at),
    )


def _truncate(
    memories: list[MemoryItem],
    max_items: int
) -> tuple[list[MemoryItem], bool]:
    """
    Truncate memory list to maximum size.
    
    Args:
        memories: Sorted list of MemoryItem instances
        max_items: Maximum number of items to keep
        
    Returns:
        Tuple of (truncated_list, was_truncated_flag)
        - truncated_list: First max_items items
        - was_truncated: True if list was shortened, False otherwise
        
    Note:
        Truncation happens after sorting, so higher-priority items
        are retained and lower-priority ones are discarded.
    """
    if len(memories) <= max_items:
        return memories, False
    
    return memories[:max_items], True