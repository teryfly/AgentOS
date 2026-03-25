"""
Test database utilities.

Manages PostgreSQL test database lifecycle and schema setup.
"""
import asyncpg
import os
from pathlib import Path


class TestPoolAdapter:
    """
    Adapter to provide DatabasePool-compatible interface over asyncpg.Pool.
    """

    __test__ = False  # Prevent pytest class collection warning

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def acquire(self):
        """Compatible with `async with db_pool.acquire() as conn`."""
        return self._pool.acquire()

    async def execute_in_transaction(self, fn):
        """Compatible with DatabasePool.execute_in_transaction()."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await fn(conn)


class TestDatabase:
    """
    Manages test database connection and schema.
    """

    __test__ = False  # Prevent pytest class collection warning

    def __init__(self):
        self._pool: asyncpg.Pool | None = None
        self._adapter: TestPoolAdapter | None = None
        self._initialized = False
        self._schema_created = False

    async def initialize(self) -> None:
        """
        Create connection pool and initialize schema.
        """
        if self._initialized:
            return

        host = os.getenv("TEST_DB_HOST", "localhost")
        port = int(os.getenv("TEST_DB_PORT", "5432"))
        database = os.getenv("TEST_DB_NAME", "agent_test_db")
        user = os.getenv("TEST_DB_USER", "agent_test_user")
        password = os.getenv("TEST_DB_PASSWORD", "test_password")

        self._pool = await asyncpg.create_pool(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            min_size=2,
            max_size=10,
            command_timeout=60,
            timeout=10,
        )
        self._adapter = TestPoolAdapter(self._pool)

        if not self._schema_created:
            await self._create_schema()
            self._schema_created = True

        self._initialized = True

    async def _create_schema(self) -> None:
        """Execute migration SQL."""
        schema_path = (
            Path(__file__).parent.parent.parent
            / "agent_os"
            / "task_center"
            / "storage"
            / "migrations"
            / "001_initial.sql"
        )

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        async with self._pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS task_runtime_states CASCADE")
            await conn.execute("DROP TABLE IF EXISTS tasks CASCADE")
            await conn.execute(schema_sql)
            print("✓ Database schema created")

    async def clear_all_data(self) -> None:
        """Delete all data from tables."""
        if not self._pool:
            raise RuntimeError("TestDatabase not initialized")

        async with self._pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE task_runtime_states, tasks CASCADE")

    def get_pool(self):
        """Get DatabasePool-compatible adapter."""
        if not self._adapter:
            raise RuntimeError("TestDatabase not initialized")
        return self._adapter

    async def cleanup(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._adapter = None
            self._initialized = False