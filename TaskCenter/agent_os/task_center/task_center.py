"""
TaskCenter facade — unified public API.

Delegates all operations to specialized components while maintaining clean interface.
"""
import logging
import time
import uuid
from typing import Any
from agent_os.common import (
    Task, TaskResult, TaskStatus, TaskBatchItem, TaskRuntimeState,
    TaskCreated
)
from agent_os.common.interfaces import EventBus
from .config import TaskCenterConfig
from .state_machine import determine_initial_status
from .graph.graph_validator import GraphValidator
from .lifecycle.lifecycle_manager import LifecycleManager
from .batch.batch_processor import BatchProcessor
from .state_ops.state_ops import StateOps
from .cleanup.cleanup_handler import CleanupHandler

logger = logging.getLogger(__name__)


class TaskCenter:
    """
    TaskCenter facade providing all task management operations.
    
    Responsibilities:
    - Task lifecycle management
    - DAG validation and dependency tracking
    - State persistence coordination
    - Domain event publishing
    """
    
    def __init__(
        self,
        task_store,
        runtime_store,
        event_bus: EventBus,
        db_pool,
        config: TaskCenterConfig | None = None
    ):
        """
        Args:
            task_store: TaskStore implementation
            runtime_store: RuntimeStateStore implementation
            event_bus: EventBus for domain events
            db_pool: DatabasePool for transactions
            config: Optional configuration (defaults used if None)
        """
        self._task_store = task_store
        self._runtime_store = runtime_store
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._config = config or TaskCenterConfig()
        
        # Initialize components
        self._graph_validator = GraphValidator(self._config.max_depth)
        self._lifecycle_manager = LifecycleManager(task_store, event_bus)
        self._batch_processor = BatchProcessor(task_store, self._graph_validator, event_bus, db_pool)
        self._state_ops = StateOps(task_store, runtime_store, self._config)
        self._cleanup_handler = CleanupHandler(runtime_store, event_bus)
    
    async def initialize(self) -> None:
        """Initialize event subscriptions."""
        await self._cleanup_handler.initialize()
        logger.info("[TaskCenter | initialize] Initialized")
    
    async def create_task(
        self,
        name: str,
        description: str,
        role: str,
        depends_on: list[str] | None = None,
        metadata: dict | None = None
    ) -> Task:
        """
        Create single task.
        
        Args:
            name: Task name
            description: Task description
            role: Actor role
            depends_on: Dependency task IDs
            metadata: Fixed metadata
            
        Returns:
            Created task
        """
        depends_on = depends_on or []
        metadata = metadata or {}
        
        # Validate dependencies exist
        for dep_id in depends_on:
            await self._task_store.get(dep_id)
        
        # Validate graph constraints
        task_id = str(uuid.uuid4())
        
        async def get_deps_fn(tid: str) -> list[str]:
            t = await self._task_store.get(tid)
            return t.depends_on
        
        await self._graph_validator.check_circular(task_id, depends_on, get_deps_fn)
        await self._graph_validator.check_depth(depends_on, get_deps_fn)
        
        # Determine initial status
        dep_statuses = []
        for dep_id in depends_on:
            dep_task = await self._task_store.get(dep_id)
            dep_statuses.append(dep_task.status)
        
        initial_status = determine_initial_status(dep_statuses)
        
        # Create task
        current_time = int(time.time() * 1000)
        task = Task(
            id=task_id,
            name=name,
            description=description,
            role=role,
            status=initial_status,
            depends_on=depends_on,
            children=[],
            result=None,
            metadata=metadata,
            created_at=current_time,
            updated_at=current_time,
            version=0
        )
        
        created = await self._task_store.create(task)
        
        # Update parent children
        for dep_id in depends_on:
            await self._task_store.add_child(dep_id, created.id)
        
        # Publish event
        await self._event_bus.publish(
            TaskCreated(task_id=created.id, name=created.name, role=created.role, status=created.status)
        )
        
        logger.info(f"[TaskCenter | create_task] Created task {created.id}")
        return created
    
    async def create_task_batch(
        self,
        items: list[TaskBatchItem],
        parent_task_id: str | None = None
    ) -> dict[str, Task]:
        """
        Atomically create batch of tasks.
        
        Args:
            items: Batch items
            parent_task_id: Optional parent to update children
            
        Returns:
            Map of ref_id to Task
        """
        return await self._batch_processor.process_batch(items, parent_task_id)
    
    async def get_task(self, task_id: str) -> Task:
        """Retrieve task by ID."""
        return await self._task_store.get(task_id)
    
    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        role: str | None = None
    ) -> list[Task]:
        """List tasks with optional filters."""
        return await self._task_store.list_by(status, role)
    
    async def get_runnable_tasks(self) -> list[Task]:
        """Get all PENDING tasks with satisfied dependencies."""
        return await self._task_store.get_runnable()
    
    async def update_status(self, task_id: str, status: TaskStatus) -> Task:
        """Update task status with validation."""
        return await self._lifecycle_manager.update_status(task_id, status)
    
    async def complete_task(self, task_id: str, result: TaskResult) -> None:
        """Mark task as completed and unblock dependents."""
        await self._lifecycle_manager.complete_task(task_id, result)
    
    async def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        await self._lifecycle_manager.fail_task(task_id, error)
    
    async def resume_task(self, task_id: str, input_data: Any) -> None:
        """Resume task from WAITING_INPUT."""
        await self._lifecycle_manager.resume_task(task_id, input_data)
    
    async def update_task_metadata(self, task_id: str, metadata_patch: dict) -> None:
        """Merge-update task metadata."""
        await self._state_ops.update_metadata(task_id, metadata_patch)
    
    async def update_task_runtime_state(self, task_id: str, runtime_patch: dict) -> None:
        """Merge-update runtime state."""
        await self._state_ops.update_runtime_state(task_id, runtime_patch)
    
    async def get_task_runtime_state(self, task_id: str) -> TaskRuntimeState | None:
        """Retrieve runtime state for task."""
        return await self._runtime_store.get(task_id)
    
    async def delete_task_runtime_state(self, task_id: str) -> None:
        """Delete runtime state (idempotent)."""
        await self._runtime_store.delete(task_id)