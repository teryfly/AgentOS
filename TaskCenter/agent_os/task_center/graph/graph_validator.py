"""
Composite graph validation interface.

Coordinates cycle detection and depth checking for both single task and batch scenarios.
"""
import logging
from typing import Callable, Awaitable
from .cycle_detector import CycleDetector
from .depth_checker import DepthChecker

logger = logging.getLogger(__name__)


class GraphValidator:
    """
    Validates DAG integrity constraints.
    """
    
    def __init__(self, max_depth: int):
        """
        Args:
            max_depth: Maximum allowed DAG nesting depth
        """
        self._cycle_detector = CycleDetector()
        self._depth_checker = DepthChecker(max_depth)
    
    async def check_circular(
        self,
        task_id: str,
        depends_on: list[str],
        get_deps_fn: Callable[[str], Awaitable[list[str]]]
    ) -> None:
        """
        Check for circular dependencies in existing graph.
        
        Args:
            task_id: Task being validated
            depends_on: Direct dependencies
            get_deps_fn: Function to fetch dependencies for any task
        """
        await self._cycle_detector.check_async(task_id, depends_on, get_deps_fn)
    
    async def check_depth(
        self,
        depends_on: list[str],
        get_deps_fn: Callable[[str], Awaitable[list[str]]]
    ) -> None:
        """
        Check depth constraint.
        
        Args:
            depends_on: Direct dependencies
            get_deps_fn: Function to fetch dependencies for any task
        """
        await self._depth_checker.check_async(depends_on, get_deps_fn)
    
    def check_circular_batch(
        self,
        ref_to_deps: dict[str, list[str]]
    ) -> None:
        """
        Check for cycles within in-memory batch.
        
        Args:
            ref_to_deps: Map of ref_id to dependency ref_ids
        """
        self._cycle_detector.check_batch(ref_to_deps)