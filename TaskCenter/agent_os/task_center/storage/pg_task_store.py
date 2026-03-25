"""
PostgreSQL implementation of TaskStore.

All operations use asyncpg for async database access.
CAS operations enforce optimistic locking via version field.
Handles UUID type conversion transparently.
"""
import logging
import time
import uuid
from typing import Any
from agent_os.common import Task, TaskStatus, TaskNotFoundError
from .interfaces import TaskStore, VersionConflict
from .task_row_mapper import TaskRowMapper

logger = logging.getLogger(__name__)


class PgTaskStore(TaskStore):
    """
    PostgreSQL-backed task storage with CAS support.
    """
    
    def __init__(self, db_pool):
        """
        Args:
            db_pool: DatabasePool instance
        """
        self._db_pool = db_pool
        self._mapper = TaskRowMapper()
    
    def _to_uuid(self, task_id: str | uuid.UUID) -> uuid.UUID:
        """Convert string task_id to UUID."""
        if isinstance(task_id, str):
            return uuid.UUID(task_id)
        return task_id
    
    async def create(self, task: Task) -> Task:
        """Create new task."""
        row_data = self._mapper.to_row(task)
        
        async with self._db_pool.acquire() as conn:
            query = """
                INSERT INTO tasks (
                    id, name, description, role, status,
                    depends_on, children, result, metadata,
                    created_at, updated_at, version
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                )
                RETURNING *
            """
            row = await conn.fetchrow(
                query,
                row_data["id"], row_data["name"], row_data["description"],
                row_data["role"], row_data["status"], row_data["depends_on"],
                row_data["children"], row_data["result"], row_data["metadata"],
                row_data["created_at"], row_data["updated_at"], row_data["version"]
            )
            
            logger.debug(f"[TaskCenter | PgTaskStore | create] Created task {row['id']}")
            return self._mapper.from_row(row)
    
    async def get(self, task_id: str) -> Task:
        """Retrieve task by ID."""
        task_uuid = self._to_uuid(task_id)
        
        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_uuid)
            
            if not row:
                raise TaskNotFoundError(f"Task {task_id} not found")
            
            return self._mapper.from_row(row)
    
    async def list_by(
        self,
        status: TaskStatus | None = None,
        role: str | None = None
    ) -> list[Task]:
        """List tasks with optional filters."""
        conditions = []
        params = []
        param_idx = 1
        
        if status is not None:
            conditions.append(f"status = ${param_idx}")
            params.append(status.value)
            param_idx += 1
        
        if role is not None:
            conditions.append(f"role = ${param_idx}")
            params.append(role)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT * FROM tasks WHERE {where_clause} ORDER BY created_at ASC"
        
        async with self._db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._mapper.from_row(row) for row in rows]
    
    async def get_runnable(self) -> list[Task]:
        """
        Get PENDING tasks with all dependencies COMPLETED.
        """
        async with self._db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tasks WHERE status = $1", TaskStatus.PENDING.value)
            
            runnable = []
            for row in rows:
                task = self._mapper.from_row(row)
                
                if not task.depends_on:
                    runnable.append(task)
                    continue
                
                # Convert depends_on to UUIDs
                dep_uuids = [self._to_uuid(dep_id) for dep_id in task.depends_on]
                
                # Check all dependencies
                dep_query = "SELECT status FROM tasks WHERE id = ANY($1)"
                dep_rows = await conn.fetch(dep_query, dep_uuids)
                
                if len(dep_rows) == len(task.depends_on):
                    if all(dep["status"] == TaskStatus.COMPLETED.value for dep in dep_rows):
                        runnable.append(task)
            
            return runnable
    
    async def update(self, task: Task) -> Task:
        """Update task with CAS on version."""
        row_data = self._mapper.to_row(task)
        
        async with self._db_pool.acquire() as conn:
            query = """
                UPDATE tasks SET
                    name = $2, description = $3, role = $4, status = $5,
                    depends_on = $6, children = $7, result = $8, metadata = $9,
                    updated_at = $10, version = $11
                WHERE id = $1 AND version = $12
                RETURNING *
            """
            
            new_version = task.version + 1
            updated_at = int(time.time() * 1000)
            
            row = await conn.fetchrow(
                query,
                row_data["id"], row_data["name"], row_data["description"],
                row_data["role"], row_data["status"], row_data["depends_on"],
                row_data["children"], row_data["result"], row_data["metadata"],
                updated_at, new_version, task.version
            )
            
            if not row:
                # Either version mismatch or task not found
                existing = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", row_data["id"])
                if not existing:
                    raise TaskNotFoundError(f"Task {task.id} not found")
                raise VersionConflict(f"Version conflict on task {task.id}")
            
            logger.debug(f"[TaskCenter | PgTaskStore | update] Updated task {task.id} to version {new_version}")
            return self._mapper.from_row(row)
    
    async def add_child(self, task_id: str, child_id: str) -> None:
        """Append child_id to task's children array."""
        task_uuid = self._to_uuid(task_id)
        
        async with self._db_pool.acquire() as conn:
            # Use jsonb_insert to append to array
            query = """
                UPDATE tasks
                SET children = children || $2::jsonb,
                    updated_at = $3
                WHERE id = $1
            """
            
            updated_at = int(time.time() * 1000)
            result = await conn.execute(query, task_uuid, f'["{child_id}"]', updated_at)
            
            if result == "UPDATE 0":
                raise TaskNotFoundError(f"Task {task_id} not found")
            
            logger.debug(f"[TaskCenter | PgTaskStore | add_child] Added child {child_id} to task {task_id}")
    
    async def cas_update_status(
        self,
        task_id: str,
        expected_version: int,
        new_status: TaskStatus
    ) -> Task:
        """Compare-And-Swap status update."""
        task_uuid = self._to_uuid(task_id)
        
        async with self._db_pool.acquire() as conn:
            query = """
                UPDATE tasks
                SET status = $2, version = version + 1, updated_at = $3
                WHERE id = $1 AND version = $4
                RETURNING *
            """
            
            updated_at = int(time.time() * 1000)
            row = await conn.fetchrow(query, task_uuid, new_status.value, updated_at, expected_version)
            
            if not row:
                existing = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_uuid)
                if not existing:
                    raise TaskNotFoundError(f"Task {task_id} not found")
                raise VersionConflict(f"Version conflict on task {task_id}")
            
            logger.debug(f"[TaskCenter | PgTaskStore | cas_update_status] Updated {task_id} to {new_status.value}")
            return self._mapper.from_row(row)
    
    async def batch_create_in_tx(
        self,
        conn: Any,
        tasks: list[Task]
    ) -> list[Task]:
        """Batch create tasks within transaction."""
        created_tasks = []
        
        for task in tasks:
            row_data = self._mapper.to_row(task)
            
            query = """
                INSERT INTO tasks (
                    id, name, description, role, status,
                    depends_on, children, result, metadata,
                    created_at, updated_at, version
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                )
                RETURNING *
            """
            row = await conn.fetchrow(
                query,
                row_data["id"], row_data["name"], row_data["description"],
                row_data["role"], row_data["status"], row_data["depends_on"],
                row_data["children"], row_data["result"], row_data["metadata"],
                row_data["created_at"], row_data["updated_at"], row_data["version"]
            )
            
            created_tasks.append(self._mapper.from_row(row))
        
        logger.info(f"[TaskCenter | PgTaskStore | batch_create_in_tx] Created {len(created_tasks)} tasks")
        return created_tasks