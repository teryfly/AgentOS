"""
PostgreSQL implementation of RuntimeStateStore.

Manages task_runtime_states table with upsert and CAS support.
Handles UUID type conversion transparently.
"""
import json
import logging
import time
import uuid
from agent_os.common import TaskRuntimeState
from .interfaces import RuntimeStateStore, VersionConflict

logger = logging.getLogger(__name__)


class PgRuntimeStateStore(RuntimeStateStore):
    """
    PostgreSQL-backed runtime state storage.
    """

    def __init__(self, db_pool):
        self._db_pool = db_pool

    def _to_uuid(self, task_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(task_id, str):
            return uuid.UUID(task_id)
        return task_id

    async def get(self, task_id: str) -> TaskRuntimeState | None:
        task_uuid = self._to_uuid(task_id)

        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM task_runtime_states WHERE task_id = $1",
                task_uuid
            )
            if not row:
                return None

            runtime_data = row["runtime_data"]
            if isinstance(runtime_data, str):
                runtime_data = json.loads(runtime_data)

            return TaskRuntimeState(
                task_id=task_id,
                runtime_data=runtime_data,
                version=row["version"],
                updated_at=row["updated_at"]
            )

    async def upsert(
        self,
        task_id: str,
        runtime_patch: dict,
        expected_version: int | None = None
    ) -> TaskRuntimeState:
        """
        Insert or update runtime state with optional CAS.
        """
        task_uuid = self._to_uuid(task_id)
        updated_at = int(time.time() * 1000)

        async with self._db_pool.acquire() as conn:
            if expected_version is None:
                # Unconditional merge-upsert
                query = """
                    INSERT INTO task_runtime_states (task_id, runtime_data, version, updated_at)
                    VALUES ($1, $2::jsonb, 0, $3)
                    ON CONFLICT (task_id) DO UPDATE SET
                        runtime_data = task_runtime_states.runtime_data || EXCLUDED.runtime_data,
                        version = task_runtime_states.version + 1,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                """
                row = await conn.fetchrow(query, task_uuid, json.dumps(runtime_patch), updated_at)
            else:
                # CAS semantics
                existing = await conn.fetchrow(
                    "SELECT runtime_data, version FROM task_runtime_states WHERE task_id = $1",
                    task_uuid
                )
                
                if existing is None:
                    if expected_version == 0:
                        # Race-safe first-write path:
                        # try insert-if-absent, else signal VersionConflict
                        insert_query = """
                            INSERT INTO task_runtime_states (task_id, runtime_data, version, updated_at)
                            VALUES ($1, $2::jsonb, 0, $3)
                            ON CONFLICT (task_id) DO NOTHING
                            RETURNING *
                        """
                        row = await conn.fetchrow(insert_query, task_uuid, json.dumps(runtime_patch), updated_at)
                        if row is None:
                            raise VersionConflict(f"Version conflict on runtime state {task_id}")
                    else:
                        raise VersionConflict(f"Runtime state {task_id} does not exist")
                else:
                    if existing["version"] != expected_version:
                        raise VersionConflict(f"Version conflict on runtime state {task_id}")

                    existing_data = existing["runtime_data"]
                    if isinstance(existing_data, str):
                        existing_data = json.loads(existing_data)

                    merged_data = {**existing_data, **runtime_patch}

                    update_query = """
                        UPDATE task_runtime_states
                        SET runtime_data = $2::jsonb,
                            version = version + 1,
                            updated_at = $3
                        WHERE task_id = $1 AND version = $4
                        RETURNING *
                    """
                    row = await conn.fetchrow(
                        update_query,
                        task_uuid,
                        json.dumps(merged_data),
                        updated_at,
                        expected_version
                    )
                    if row is None:
                        raise VersionConflict(f"Version conflict on runtime state {task_id}")

            runtime_data = row["runtime_data"]
            if isinstance(runtime_data, str):
                runtime_data = json.loads(runtime_data)

            logger.debug(f"[TaskCenter | PgRuntimeStateStore | upsert] Updated runtime state for {task_id}")

            return TaskRuntimeState(
                task_id=task_id,
                runtime_data=runtime_data,
                version=row["version"],
                updated_at=row["updated_at"]
            )

    async def delete(self, task_id: str) -> None:
        task_uuid = self._to_uuid(task_id)

        async with self._db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM task_runtime_states WHERE task_id = $1",
                task_uuid
            )
            logger.debug(f"[TaskCenter | PgRuntimeStateStore | delete] Deleted runtime state for {task_id}")