"""
DAG depth validation using BFS upward traversal.

Computes maximum depth from dependencies and enforces max_depth limit.

Depth Definition:
- Root nodes (no dependencies): depth = 0
- Node with dependencies: depth = max(dependency depths) + 1
- max_depth constraint: node depth must be <= max_depth
"""
import logging
from typing import Callable, Awaitable
from collections import deque
from agent_os.common import MaxDepthExceededError

logger = logging.getLogger(__name__)


class DepthChecker:
    """
    Validates task graph depth constraints.
    """
    
    def __init__(self, max_depth: int):
        """
        Args:
            max_depth: Maximum allowed DAG nesting depth (inclusive)
        """
        self._max_depth = max_depth
    
    async def check_async(
        self,
        depends_on: list[str],
        get_deps_fn: Callable[[str], Awaitable[list[str]]]
    ) -> None:
        """
        Check if new task with given dependencies would exceed max_depth.
        
        Algorithm:
        1. Use BFS to compute depth of each dependency
        2. New task depth = max(dependency depths) + 1
        3. Reject if new task depth > max_depth
        
        Args:
            depends_on: Direct dependencies of new task
            get_deps_fn: Async function to fetch dependencies for a task ID
            
        Raises:
            MaxDepthExceededError: Depth exceeds max_depth
        """
        if not depends_on:
            # Root task, depth = 0
            return
        
        # Compute depth for all dependencies using BFS
        depth_map = {}  # task_id -> depth
        
        async def compute_depth(task_id: str) -> int:
            """Compute depth of a task recursively with memoization."""
            if task_id in depth_map:
                return depth_map[task_id]
            
            # Fetch this task's dependencies
            parent_deps = await get_deps_fn(task_id)
            
            if not parent_deps:
                # This is a root node
                depth = 0
            else:
                # Depth = max(parent depths) + 1
                parent_depths = []
                for parent_id in parent_deps:
                    parent_depth = await compute_depth(parent_id)
                    parent_depths.append(parent_depth)
                depth = max(parent_depths) + 1
            
            depth_map[task_id] = depth
            return depth
        
        # Compute depth for all direct dependencies
        max_dep_depth = 0
        for dep_id in depends_on:
            dep_depth = await compute_depth(dep_id)
            max_dep_depth = max(max_dep_depth, dep_depth)
        
        # New task depth = max(dependency depths) + 1
        new_task_depth = max_dep_depth + 1
        
        if new_task_depth > self._max_depth:
            raise MaxDepthExceededError(
                f"Task depth {new_task_depth} exceeds maximum {self._max_depth}"
            )
        
        logger.debug(
            f"[TaskCenter | DepthChecker | check_async] "
            f"New task depth: {new_task_depth}, max allowed: {self._max_depth}"
        )