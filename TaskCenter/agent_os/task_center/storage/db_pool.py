"""
AsyncPG connection pool manager.

Manages lifecycle of PostgreSQL connection pool using asyncpg.
Reads configuration from environment variables.
"""
import os
import asyncpg
import logging
from contextlib import asynccontextmanager
from typing import Callable, Any, AsyncContextManager

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    Manages asyncpg connection pool lifecycle.
    
    Provides transaction support and connection acquisition.
    """
    
    def __init__(self):
        self._pool: asyncpg.Pool | None = None
    
    async def initialize(self) -> None:
        """
        Initialize connection pool from environment variables.
        
        Required env vars:
            - DB_HOST: PostgreSQL host
            - DB_PORT: PostgreSQL port
            - DB_NAME: Database name
            - DB_USER: Database user
            - DB_PASSWORD: Database password
        """
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "5432"))
        database = os.getenv("DB_NAME", "agent_db")
        user = os.getenv("DB_USER", "agent_user")
        password = os.getenv("DB_PASSWORD", "")
        
        logger.info(f"[TaskCenter | DatabasePool | initialize] Connecting to {host}:{port}/{database}")
        
        self._pool = await asyncpg.create_pool(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            min_size=5,
            max_size=20
        )
        
        logger.info("[TaskCenter | DatabasePool | initialize] Connection pool created")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[asyncpg.Connection]:
        """
        Acquire connection from pool.
        
        Usage:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
        """
        if not self._pool:
            raise RuntimeError("DatabasePool not initialized")
        
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute_in_transaction(self, fn: Callable[[asyncpg.Connection], Any]) -> Any:
        """
        Execute function within transaction context.
        
        Args:
            fn: Async function taking connection as argument
            
        Returns:
            Function return value
            
        Raises:
            Exception propagated from fn (triggers rollback)
        """
        async with self.acquire() as conn:
            async with conn.transaction():
                return await fn(conn)
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("[TaskCenter | DatabasePool | close] Connection pool closed")