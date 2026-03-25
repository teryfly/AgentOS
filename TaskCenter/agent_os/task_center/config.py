"""
TaskCenter configuration.

Defines tunable parameters for task management behavior.
"""
from dataclasses import dataclass


@dataclass
class TaskCenterConfig:
    """
    Configuration for TaskCenter behavior.
    
    Attributes:
        max_depth: Maximum allowed DAG nesting depth (prevents infinite recursion)
        max_metadata_retries: Number of retries for optimistic lock conflicts on metadata updates
        max_runtime_retries: Number of retries for optimistic lock conflicts on runtime state updates
        poll_interval_ms: Polling interval for runnable tasks (used by AgentRuntime, not TaskCenter)
    """
    max_depth: int = 10
    max_metadata_retries: int = 3
    max_runtime_retries: int = 3
    poll_interval_ms: int = 500  # For AgentRuntime reference