"""
Unit tests for DepthChecker.

Depth semantics:
- Root node (no deps): depth = 0
- Node with deps: depth = max(dep_depths) + 1
- max_depth is inclusive: depth <= max_depth is allowed
"""
import pytest
from agent_os.common import MaxDepthExceededError
from agent_os.task_center.graph.depth_checker import DepthChecker


class TestDepthChecker:
    """Test DAG depth validation."""
    
    @pytest.mark.asyncio
    async def test_no_dependencies_has_depth_zero(self):
        """Root task with no dependencies should pass (depth=0)."""
        checker = DepthChecker(max_depth=5)
        
        async def get_deps_fn(task_id: str):
            return []
        
        # Should not raise (depth = 0)
        await checker.check_async([], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_depth_within_limit_passes(self):
        """Depth < max_depth should pass."""
        checker = DepthChecker(max_depth=5)
        
        # Chain: C → B → A (A is root)
        # A: depth 0
        # B: depth 1
        # C: depth 2
        # New task depending on C: depth 3 (< 5, should pass)
        graph = {
            "A": [],
            "B": ["A"],
            "C": ["B"]
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        # New task depends on C (depth 2), so new task depth = 3
        await checker.check_async(["C"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_depth_at_limit_passes(self):
        """Depth == max_depth should pass (inclusive limit)."""
        checker = DepthChecker(max_depth=3)
        
        # Chain: C → B → A
        # A: depth 0
        # B: depth 1
        # C: depth 2
        # New task depending on C: depth 3 (== 3, should PASS)
        graph = {
            "A": [],
            "B": ["A"],
            "C": ["B"]
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        # New task depth = 3, max_depth = 3, should pass
        await checker.check_async(["C"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_depth_exceeds_limit_raises_error(self):
        """Depth > max_depth should raise MaxDepthExceededError."""
        checker = DepthChecker(max_depth=2)
        
        # Chain: C → B → A
        # A: depth 0
        # B: depth 1
        # C: depth 2
        # New task depending on C: depth 3 (> 2, should REJECT)
        graph = {
            "A": [],
            "B": ["A"],
            "C": ["B"]
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        with pytest.raises(MaxDepthExceededError):
            await checker.check_async(["C"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_diamond_uses_max_depth(self):
        """Diamond pattern should use longest path for depth calculation."""
        checker = DepthChecker(max_depth=3)
        
        # Diamond with different path lengths:
        #     A (depth 0)
        #    / \
        #   B   C (both depth 1)
        #    \ /
        #     D (would be depth 2)
        # New task E depending on B,C: depth = max(1,1) + 1 = 2
        graph = {
            "A": [],
            "B": ["A"],
            "C": ["A"],
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        # New task depends on B and C (both depth 1)
        # New task depth = max(1, 1) + 1 = 2 (< 3, should pass)
        await checker.check_async(["B", "C"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_uneven_diamond_max_path(self):
        """Diamond with uneven paths should use longest path."""
        checker = DepthChecker(max_depth=4)
        
        # Uneven diamond:
        #     A (depth 0)
        #    / \
        #   B   C (depth 1)
        #   |   |
        #   D   E (D: depth 2, E: depth 2)
        #    \ /
        #     F (would be depth 3)
        # New task depending on D, E: depth = max(2,2) + 1 = 3
        graph = {
            "A": [],
            "B": ["A"],
            "C": ["A"],
            "D": ["B"],
            "E": ["C"]
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        # New task depends on D and E (both depth 2)
        # New task depth = 3 (< 4, should pass)
        await checker.check_async(["D", "E"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_multiple_root_dependencies(self):
        """Task depending on multiple roots should have depth 1."""
        checker = DepthChecker(max_depth=5)
        
        # Multiple roots: A, B, C all at depth 0
        graph = {
            "A": [],
            "B": [],
            "C": []
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        # New task depends on A, B, C (all depth 0)
        # New task depth = max(0, 0, 0) + 1 = 1
        await checker.check_async(["A", "B", "C"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_single_dependency_at_max_depth(self):
        """Single dependency at max_depth-1 should allow new task at max_depth."""
        checker = DepthChecker(max_depth=2)
        
        # B → A
        # A: depth 0
        # B: depth 1
        # New task depending on B: depth 2 (== max_depth, should pass)
        graph = {
            "A": [],
            "B": ["A"]
        }
        
        async def get_deps_fn(task_id: str) -> list[str]:
            return graph.get(task_id, [])
        
        await checker.check_async(["B"], get_deps_fn)