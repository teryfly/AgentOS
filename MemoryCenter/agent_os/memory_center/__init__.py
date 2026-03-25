"""
MemoryCenter public exports.

This module exposes the public API for memory management.
All other modules should import from this package, not from submodules.

Usage:
    from agent_os.memory_center import MemoryCenter, create_memory_center_from_env
    
    # Create from environment
    memory_center = create_memory_center_from_env()
    await memory_center._storage.initialize()
    
    # Use memory_center
    await memory_center.write(memory_item)
    context = await memory_center.build_context(task_id)
    
    # Cleanup
    await memory_center.close()
"""

from .config import create_memory_center_from_env
from .memory_center import MemoryCenter

__all__ = [
    "MemoryCenter",
    "create_memory_center_from_env",
]