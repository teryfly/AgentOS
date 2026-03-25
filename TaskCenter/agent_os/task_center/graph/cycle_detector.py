"""
Circular dependency detection using DFS.

Implements both async (for existing graph) and sync (for in-memory batch) variants.
"""
import logging
from typing import Callable, Awaitable
from agent_os.common import CircularDependencyError

logger = logging.getLogger(__name__)


class CycleDetector:
    """
    Detects cycles in task dependency graphs.
    """
    
    @staticmethod
    async def check_async(
        task_id: str,
        depends_on: list[str],
        get_deps_fn: Callable[[str], Awaitable[list[str]]]
    ) -> None:
        """
        Async DFS for existing graph stored in database.
        
        Args:
            task_id: Starting task ID
            depends_on: Direct dependencies of task
            get_deps_fn: Async function to fetch dependencies for a task ID
            
        Raises:
            CircularDependencyError: Cycle detected
        """
        visited = set()
        rec_stack = set()
        
        async def dfs(node: str) -> None:
            if node in rec_stack:
                raise CircularDependencyError(f"Circular dependency detected involving task {node}")
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            # Fetch dependencies for this node
            deps = await get_deps_fn(node)
            for dep in deps:
                await dfs(dep)
            
            rec_stack.remove(node)
        
        # Check if adding depends_on would create cycle
        for dep in depends_on:
            await dfs(dep)
    
    @staticmethod
    def check_batch(
        ref_to_deps: dict[str, list[str]]
    ) -> None:
        """
        Synchronous DFS for in-memory batch graph.
        
        Args:
            ref_to_deps: Map of ref_id to list of dependency ref_ids
            
        Raises:
            CircularDependencyError: Cycle detected in batch
        """
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> None:
            if node in rec_stack:
                raise CircularDependencyError(f"Circular dependency detected in batch involving {node}")
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            deps = ref_to_deps.get(node, [])
            for dep in deps:
                dfs(dep)
            
            rec_stack.remove(node)
        
        # Check all nodes
        for ref_id in ref_to_deps:
            if ref_id not in visited:
                dfs(ref_id)