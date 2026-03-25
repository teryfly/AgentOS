"""
PostgreSQL storage implementation using asyncpg.

This module provides async database operations with:
- Connection pooling for efficient resource usage
- Chinese full-text search using PGroonga (with fallback to PostgreSQL built-in)
- Support for cross-task global search (task_id=None)
- Graceful degradation on failures
"""

import logging
import os
from typing import Optional
from urllib.parse import quote_plus
import uuid

import asyncpg

from agent_os.common import MemoryItem, MemoryType

from .serialization import memory_item_to_row, rows_to_batch

logger = logging.getLogger(__name__)


class PostgresMemoryStorage:
    """
    Async PostgreSQL storage implementation for memory items.

    Features:
    - Connection pooling (min=10, max=20 by default)
    - Chinese full-text search with PGroonga (or PostgreSQL built-in fallback)
    - Cross-task search support (task_id=None)
    - All operations are async

    Search Methods:
    - PGroonga: Best for Chinese/Japanese/multilingual text (requires extension)
    - PostgreSQL built-in: Fallback using GIN indexes with 'simple' config
    - ILIKE: Ultimate fallback for pattern matching

    Configuration:
        Reads from environment variables:
        - DB_HOST (default: localhost)
        - DB_PORT (default: 5432)
        - DB_NAME (required)
        - DB_USER (required)
        - DB_PASSWORD (required)
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        **pool_kwargs
    ) -> None:
        """
        Initialize PostgreSQL storage.

        Args:
            dsn: PostgreSQL connection string. If None, builds from env vars.
            **pool_kwargs: Additional arguments for asyncpg.create_pool
                          (e.g., min_size, max_size, command_timeout)
        """
        self._dsn = dsn or self._build_dsn_from_env()
        self._pool_kwargs = {
            "min_size": 10,
            "max_size": 20,
            "command_timeout": 30,
            **pool_kwargs,
        }
        self._pool: Optional[asyncpg.Pool] = None
        self._search_method: Optional[str] = None

    async def initialize(self) -> None:
        """
        Create asyncpg connection pool and detect search method.

        Must be called once at system startup before any operations.

        Raises:
            Exception: If connection pool creation fails (fail-fast)
        """
        if self._pool is not None:
            logger.warning("PostgresMemoryStorage already initialized")
            return

        try:
            self._pool = await asyncpg.create_pool(self._dsn, **self._pool_kwargs)
            
            # Detect available search method
            async with self._pool.acquire() as conn:
                try:
                    # Check if pgroonga extension is installed
                    has_pgroonga = await conn.fetchval(
                        "SELECT 1 FROM pg_extension WHERE extname = 'pgroonga'"
                    )
                    if has_pgroonga:
                        self._search_method = 'pgroonga'
                    else:
                        self._search_method = 'builtin'
                except Exception as e:
                    logger.warning(f"Failed to query pg_extension: {e}")
                    self._search_method = 'builtin'
                
            logger.info(
                f"PostgresMemoryStorage initialized with search method: "
                f"{self._search_method}"
            )
            
            if self._search_method == 'pgroonga':
                logger.info("PGroonga enabled - optimal Chinese full-text search available")
            else:
                logger.warning(
                    "PGroonga not available - using PostgreSQL built-in search. "
                    "For better Chinese support, install PGroonga: "
                    "https://pgroonga.github.io/install/"
                )
                
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    async def close(self) -> None:
        """Close the connection pool and release all resources."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgresMemoryStorage connection pool closed")

    async def save(self, memory: MemoryItem) -> None:
        """
        Insert a single memory item into the database.

        Args:
            memory: MemoryItem to persist

        Raises:
            Exception: Database errors (caught by facade)
        """
        row = memory_item_to_row(memory)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_items
                (id, task_id, type, source, content, metadata, created_at)
                VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, $7)
                """,
                row["id"],
                row["task_id"],
                row["type"],
                row["source"],
                row["content"],
                row["metadata"],
                row["created_at"],
            )

    async def save_batch(self, memories: list[MemoryItem]) -> None:
        """
        Insert multiple memory items in a batch operation.

        Uses executemany for efficiency. Partial failures are logged but
        do not stop the operation.

        Args:
            memories: List of MemoryItem instances to persist
        """
        if not memories:
            return

        rows = [memory_item_to_row(item) for item in memories]

        async with self._pool.acquire() as conn:
            try:
                await conn.executemany(
                    """
                    INSERT INTO memory_items
                    (id, task_id, type, source, content, metadata, created_at)
                    VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb, $7)
                    """,
                    [
                        (
                            r["id"],
                            r["task_id"],
                            r["type"],
                            r["source"],
                            r["content"],
                            r["metadata"],
                            r["created_at"],
                        )
                        for r in rows
                    ],
                )
            except Exception as e:
                logger.warning(f"Batch save partial failure: {e}")

    async def query_by_task(
        self,
        task_id: str,
        types: Optional[list[MemoryType]] = None
    ) -> list[MemoryItem]:
        """
        Retrieve memories for a specific task, optionally filtered by type.

        Args:
            task_id: Task identifier
            types: Optional list of MemoryType to filter by

        Returns:
            List of MemoryItem instances, ordered by created_at DESC
        """
        sql = "SELECT * FROM memory_items WHERE task_id = $1"
        params: list = [task_id]

        if types:
            type_values = [t.value for t in types]
            sql += " AND type = ANY($2::varchar[])"
            params.append(type_values)

        sql += " ORDER BY created_at DESC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return rows_to_batch([dict(row) for row in rows])

    async def search_keyword(
        self,
        query: str,
        task_id: Optional[str] = None,
        top_k: int = 5
    ) -> list[MemoryItem]:
        """
        Full-text search with Chinese support using PGroonga or PostgreSQL built-in.

        Args:
            query: Search query string (supports Chinese and English)
            task_id: Optional task scope. If None, performs global cross-task search.
            top_k: Maximum number of results

        Returns:
            List of MemoryItem instances, ordered by relevance
            
        Note:
            Uses PGroonga if available (best for Chinese), otherwise falls back to:
            1. PostgreSQL built-in full-text search with 'simple' config
            2. ILIKE pattern matching (if all else fails)
        """
        if not query.strip():
            return []

        query_text = query.strip()

        try:
            if self._search_method == 'pgroonga':
                return await self._search_pgroonga(query_text, task_id, top_k)
            else:
                return await self._search_builtin(query_text, task_id, top_k)
        except Exception as e:
            logger.warning(f"Full-text search failed: {e}, falling back to LIKE search")
            # Ultimate fallback to pattern matching
            return await self._search_like(query_text, task_id, top_k)

    async def _search_pgroonga(
        self,
        query: str,
        task_id: Optional[str],
        top_k: int
    ) -> list[MemoryItem]:
        """
        Full-text search using PGroonga extension.
        
        PGroonga provides excellent Chinese/Japanese/multilingual search capabilities.
        Uses &@~ operator for full-text search with automatic tokenization.
        """
        if task_id is not None:
            # Task-scoped search with PGroonga
            sql = """
                SELECT *, 
                       pgroonga_score(tableoid, ctid) as score
                FROM memory_items
                WHERE content &@~ $1
                  AND task_id = $2
                ORDER BY score DESC, created_at DESC
                LIMIT $3
            """
            params = [query, task_id, top_k]
        else:
            # Cross-task global search with PGroonga
            sql = """
                SELECT *, 
                       pgroonga_score(tableoid, ctid) as score
                FROM memory_items
                WHERE content &@~ $1
                ORDER BY score DESC, created_at DESC
                LIMIT $2
            """
            params = [query, top_k]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        # Remove score column before converting to MemoryItem
        result_rows = []
        for row in rows:
            row_dict = dict(row)
            row_dict.pop('score', None)
            result_rows.append(row_dict)

        return rows_to_batch(result_rows)

    async def _search_builtin(
        self,
        query: str,
        task_id: Optional[str],
        top_k: int
    ) -> list[MemoryItem]:
        """
        Full-text search using PostgreSQL built-in capabilities.
        
        Uses 'simple' text search configuration for language-agnostic tokenization.
        Less effective for Chinese but works as fallback.
        """
        if task_id is not None:
            # Task-scoped search with PostgreSQL built-in
            sql = """
                SELECT *, 
                       ts_rank(to_tsvector('simple', content), 
                               plainto_tsquery('simple', $1)) as rank
                FROM memory_items
                WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', $1)
                  AND task_id = $2
                ORDER BY rank DESC, created_at DESC
                LIMIT $3
            """
            params = [query, task_id, top_k]
        else:
            # Cross-task global search with PostgreSQL built-in
            sql = """
                SELECT *, 
                       ts_rank(to_tsvector('simple', content), 
                               plainto_tsquery('simple', $1)) as rank
                FROM memory_items
                WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', $1)
                ORDER BY rank DESC, created_at DESC
                LIMIT $2
            """
            params = [query, top_k]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        # Remove rank column before converting to MemoryItem
        result_rows = []
        for row in rows:
            row_dict = dict(row)
            row_dict.pop('rank', None)
            result_rows.append(row_dict)

        return rows_to_batch(result_rows)

    async def _search_like(
        self,
        query: str,
        task_id: Optional[str],
        top_k: int
    ) -> list[MemoryItem]:
        """
        Fallback search using ILIKE pattern matching.
        
        Used when full-text search is not available or fails.
        Works for exact substring matching but no relevance ranking.
        """
        # Escape special characters for LIKE pattern
        pattern = f"%{query}%"
        
        if task_id is not None:
            sql = """
                SELECT *
                FROM memory_items
                WHERE content ILIKE $1
                  AND task_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            """
            params = [pattern, task_id, top_k]
        else:
            sql = """
                SELECT *
                FROM memory_items
                WHERE content ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            params = [pattern, top_k]

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return rows_to_batch([dict(row) for row in rows])

    async def delete(self, memory_id: str) -> None:
        """
        Delete a specific memory by ID.

        Args:
            memory_id: Unique identifier of the memory to delete
        """
        # Convert string to UUID if needed
        try:
            memory_uuid = uuid.UUID(memory_id) if not isinstance(memory_id, uuid.UUID) else memory_id
        except ValueError:
            logger.warning(f"Invalid UUID format for memory_id: {memory_id}")
            return
            
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM memory_items WHERE id = $1",
                memory_uuid
            )

    async def delete_by_task(
        self,
        task_id: str,
        types: Optional[list[MemoryType]] = None
    ) -> None:
        """
        Delete all memories for a task, optionally filtered by type.

        Args:
            task_id: Task identifier
            types: Optional list of MemoryType to delete
        """
        sql = "DELETE FROM memory_items WHERE task_id = $1"
        params: list = [task_id]

        if types:
            type_values = [t.value for t in types]
            sql += " AND type = ANY($2::varchar[])"
            params.append(type_values)

        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    def _build_dsn_from_env(self) -> str:
        """
        Build PostgreSQL DSN from environment variables.

        Returns:
            Connection string in format:
            postgresql://user:password@host:port/database

        Raises:
            ValueError: If required environment variables are missing
        """
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        if not all([name, user, password]):
            raise ValueError(
                "Missing required environment variables: "
                "DB_NAME, DB_USER, and/or DB_PASSWORD"
            )

        # URL-encode password to support special characters like @, :, /, ?
        encoded_password = quote_plus(password)

        return f"postgresql://{user}:{encoded_password}@{host}:{port}/{name}"