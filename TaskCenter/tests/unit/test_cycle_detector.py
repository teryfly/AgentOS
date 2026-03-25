"""
Unit tests for CycleDetector.
"""
import pytest
from agent_os.common import CircularDependencyError
from agent_os.task_center.graph.cycle_detector import CycleDetector


class TestCheckAsync:
    """Test async cycle detection for existing graph."""
    
    @pytest.mark.asyncio
    async def test_no_cycle_linear_chain(self):
        """Linear dependency chain should not raise error."""
        # A → B → C (no cycle)
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": []
        }
        
        async def get_deps_fn(task_id: str):
            return graph.get(task_id, [])
        
        # Should not raise
        await CycleDetector.check_async("A", ["B"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_cycle_direct_loop(self):
        """Direct cycle A → B → A should be detected."""
        graph = {
            "A": ["B"],
            "B": ["A"]
        }
        
        async def get_deps_fn(task_id: str):
            return graph.get(task_id, [])
        
        with pytest.raises(CircularDependencyError):
            await CycleDetector.check_async("A", ["B"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_cycle_indirect_loop(self):
        """Indirect cycle A → B → C → A should be detected."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"]
        }
        
        async def get_deps_fn(task_id: str):
            return graph.get(task_id, [])
        
        with pytest.raises(CircularDependencyError):
            await CycleDetector.check_async("A", ["B"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_self_cycle(self):
        """Self-reference A → A should be detected."""
        graph = {"A": ["A"]}
        
        async def get_deps_fn(task_id: str):
            return graph.get(task_id, [])
        
        with pytest.raises(CircularDependencyError):
            await CycleDetector.check_async("A", ["A"], get_deps_fn)
    
    @pytest.mark.asyncio
    async def test_diamond_dependency_no_cycle(self):
        """Diamond pattern should not be detected as cycle."""
        # A → B, A → C, B → D, C → D
        graph = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": []
        }
        
        async def get_deps_fn(task_id: str):
            return graph.get(task_id, [])
        
        # Should not raise
        await CycleDetector.check_async("A", ["B", "C"], get_deps_fn)


class TestCheckBatch:
    """Test synchronous cycle detection for in-memory batch."""
    
    def test_no_cycle_in_batch(self):
        """Batch with no cycles should pass."""
        ref_to_deps = {
            "task1": [],
            "task2": ["task1"],
            "task3": ["task2"]
        }
        
        # Should not raise
        CycleDetector.check_batch(ref_to_deps)
    
    def test_cycle_in_batch(self):
        """Batch with internal cycle should raise error."""
        ref_to_deps = {
            "task1": ["task2"],
            "task2": ["task3"],
            "task3": ["task1"]
        }
        
        with pytest.raises(CircularDependencyError):
            CycleDetector.check_batch(ref_to_deps)
    
    def test_batch_diamond_no_cycle(self):
        """Diamond pattern in batch should pass."""
        ref_to_deps = {
            "task1": [],
            "task2": ["task1"],
            "task3": ["task1"],
            "task4": ["task2", "task3"]
        }
        
        # Should not raise
        CycleDetector.check_batch(ref_to_deps)
    
    def test_batch_self_reference(self):
        """Self-reference in batch should raise error."""
        ref_to_deps = {
            "task1": ["task1"]
        }
        
        with pytest.raises(CircularDependencyError):
            CycleDetector.check_batch(ref_to_deps)