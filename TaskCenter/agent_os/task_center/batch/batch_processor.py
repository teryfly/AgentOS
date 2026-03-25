"""
Atomic batch task creation orchestrator.

Coordinates validation, resolution, and transactional persistence.
"""
import logging
import time
import uuid
import json
from collections import defaultdict
from typing import Any, Callable, Awaitable
from agent_os.common import Task, TaskBatchItem, TaskCreated, TaskStatus
from agent_os.common.interfaces import EventBus
from ..state_machine import determine_initial_status
from .ref_resolver import RefResolver
from .batch_validator import BatchValidator

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Orchestrates atomic batch task creation.
    """

    def __init__(self, task_store, graph_validator, event_bus: EventBus, db_pool):
        """
        Args:
            task_store: TaskStore instance
            graph_validator: GraphValidator instance
            event_bus: EventBus for publishing TaskCreated events
            db_pool: DatabasePool for transaction management (or compatible asyncpg pool)
        """
        self._task_store = task_store
        self._graph_validator = graph_validator
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._validator = BatchValidator(task_store)

    async def _execute_in_transaction(self, fn: Callable[[Any], Awaitable[Any]]) -> Any:
        """
        Execute function in transaction.

        Supports both:
        - DatabasePool with execute_in_transaction()
        - Raw asyncpg pool with acquire() + conn.transaction()
        """
        if hasattr(self._db_pool, "execute_in_transaction"):
            return await self._db_pool.execute_in_transaction(fn)

        async with self._db_pool.acquire() as conn:
            async with conn.transaction():
                return await fn(conn)

    async def process_batch(
        self,
        items: list[TaskBatchItem],
        parent_task_id: str | None = None
    ) -> dict[str, Task]:
        """
        Process batch creation atomically.

        Args:
            items: Batch items to create
            parent_task_id: Optional parent task to update children

        Returns:
            Map of ref_id to created Task
        """
        # Step 1: Check ref_id uniqueness
        self._validator.check_ref_uniqueness(items)

        # Step 2: Generate task_ids
        ref_to_id = RefResolver.generate_id_map(items)
        internal_ids = set(ref_to_id.values())

        # Step 3: Resolve dependencies and build reverse children map
        resolved_items: list[tuple[TaskBatchItem, list[str]]] = []
        external_deps: set[str] = set()
        task_dep_map: dict[str, list[str]] = {}  # task_id -> resolved depends_on
        parent_to_new_children = defaultdict(list)

        for item in items:
            resolved_deps = RefResolver.resolve_dependencies(item, ref_to_id)
            resolved_items.append((item, resolved_deps))
            task_id = ref_to_id[item.ref_id]
            task_dep_map[task_id] = resolved_deps

            # Track external dependencies and build children mappings
            for dep_id in resolved_deps:
                parent_to_new_children[dep_id].append(task_id)
                if dep_id not in internal_ids:
                    external_deps.add(dep_id)

        # Step 4: Validate external dependencies exist
        await self._validator.check_external_deps_exist(external_deps)

        # Step 5: Check circular dependencies in batch refs
        ref_to_deps = {item.ref_id: item.depends_on_refs for item in items}
        self._graph_validator.check_circular_batch(ref_to_deps)

        # Step 6: Build tasks and check depth
        tasks: list[Task] = []
        current_time = int(time.time() * 1000)

        async def get_deps_fn(tid: str) -> list[str]:
            # First resolve from in-memory batch graph
            if tid in task_dep_map:
                return task_dep_map[tid]
            # Otherwise from persisted tasks
            task = await self._task_store.get(tid)
            return task.depends_on

        for item, resolved_deps in resolved_items:
            # Depth check with in-memory + persisted graph
            await self._graph_validator.check_depth(resolved_deps, get_deps_fn)

            # Determine initial status:
            # Any internal dependency is not completed at creation time
            has_internal_dep = any(dep_id in internal_ids for dep_id in resolved_deps)

            dep_statuses = []
            for dep_id in resolved_deps:
                if dep_id in internal_ids:
                    dep_statuses.append(TaskStatus.PENDING)
                else:
                    dep_task = await self._task_store.get(dep_id)
                    dep_statuses.append(dep_task.status)

            initial_status = determine_initial_status(dep_statuses)
            if has_internal_dep and initial_status == TaskStatus.PENDING:
                initial_status = TaskStatus.WAITING_DEPENDENCY

            task_id = ref_to_id[item.ref_id]
            task = Task(
                id=task_id,
                name=item.name,
                description=item.description,
                role=item.role,
                status=initial_status,
                depends_on=resolved_deps,
                children=parent_to_new_children.get(task_id, []),  # Assign internal children
                result=None,
                metadata=item.metadata,
                created_at=current_time,
                updated_at=current_time,
                version=0
            )
            tasks.append(task)

        # Step 7: Atomic transaction
        async def create_in_tx(conn):
            created = await self._task_store.batch_create_in_tx(conn, tasks)

            # Update parent if provided
            if parent_task_id:
                query = """
                    UPDATE tasks
                    SET children = children || $2::jsonb, updated_at = $3
                    WHERE id = $1
                """
                p_uuid = uuid.UUID(parent_task_id) if isinstance(parent_task_id, str) else parent_task_id
                await conn.execute(
                    query,
                    p_uuid,
                    json.dumps([t.id for t in created]),
                    int(time.time() * 1000)
                )

            # Update external dependencies' children arrays
            for ext_dep_id in external_deps:
                new_children = parent_to_new_children[ext_dep_id]
                if new_children:
                    query = """
                        UPDATE tasks
                        SET children = children || $2::jsonb, updated_at = $3
                        WHERE id = $1
                    """
                    ext_uuid = uuid.UUID(ext_dep_id) if isinstance(ext_dep_id, str) else ext_dep_id
                    await conn.execute(
                        query,
                        ext_uuid,
                        json.dumps(new_children),
                        int(time.time() * 1000)
                    )

            return created

        created_tasks = await self._execute_in_transaction(create_in_tx)

        # Step 8: Publish events
        for task in created_tasks:
            await self._event_bus.publish(
                TaskCreated(task_id=task.id, name=task.name, role=task.role, status=task.status)
            )

        # Step 9: Return ref_id map
        result = {}
        for item, task in zip(items, created_tasks):
            result[item.ref_id] = task

        logger.info(f"[TaskCenter | BatchProcessor | process_batch] Created {len(created_tasks)} tasks")
        return result