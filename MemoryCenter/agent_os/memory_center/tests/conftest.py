"""
Shared pytest fixtures for MemoryCenter tests.

This module provides reusable fixtures for both unit and integration tests,
including database connections, mock clients, and test data factories.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import httpx
import pytest
import pytest_asyncio

# Ensure project root is in sys.path so `agent_os.memory_center` can be imported
# even when pytest is executed inside `agent_os/memory_center` directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_os.common import (  # noqa: E402
    LlmGatewayConfig,
    MemoryConfig,
    MemoryItem,
    MemorySource,
    MemoryType,
)
from agent_os.memory_center.storage import PostgresMemoryStorage  # noqa: E402


def _build_test_dsn() -> str:
    """Build DSN with URL-encoded password to avoid parsing issues for special chars."""
    host = os.getenv("TEST_DB_HOST") or os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("TEST_DB_PORT") or os.getenv("DB_PORT", "5433"))
    name = os.getenv("TEST_DB_NAME") or os.getenv("DB_NAME", "agent_db")
    user = os.getenv("TEST_DB_USER") or os.getenv("DB_USER", "agent_user")
    password = os.getenv("TEST_DB_PASSWORD") or os.getenv("DB_PASSWORD", "123@lab")
    encoded_password = quote_plus(password)
    return f"postgresql://{user}:{encoded_password}@{host}:{port}/{name}"


@pytest_asyncio.fixture
async def pg_pool():
    """
    Create a PostgreSQL connection pool for tests.

    Function-scoped to avoid cross-loop/cross-test interference issues
    in newer pytest-asyncio versions.
    """
    dsn = _build_test_dsn()
    pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=3,
        command_timeout=30,
    )
    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture
async def clean_db(pg_pool) -> None:
    """
    Clean the memory_items table before each test.

    Ensures test isolation by removing all data from previous tests.
    """
    async with pg_pool.acquire() as conn:
        await conn.execute("DELETE FROM memory_items")


@pytest.fixture
def mock_httpx_client() -> httpx.AsyncClient:
    """
    Create a mock httpx.AsyncClient for unit tests.

    Returns a MagicMock that can be configured with custom responses.
    """
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def sample_memory_item():
    """
    Factory fixture for creating test MemoryItem instances.

    Usage:
        item = sample_memory_item(task_id="task-1", type_=MemoryType.SHORT)
    
    Note: 
        If task_id is not provided or is a simple string like "task-001",
        it will be converted to a UUID-like format for database compatibility.
    """

    def _create(
        task_id: Optional[str] = None,
        type_: MemoryType = MemoryType.SHORT,
        source: MemorySource = MemorySource.ACTOR,
        content: Optional[dict] = None,
        metadata: Optional[dict] = None,
        created_at: Optional[int] = None,
    ) -> MemoryItem:
        import time

        # Generate UUID-based task_id if not provided
        if task_id is None:
            task_id = str(uuid.uuid4())

        if content is None:
            content = {"message": "test content"}

        if metadata is None:
            metadata = {}

        if created_at is None:
            created_at = int(time.time() * 1000)

        return MemoryItem(
            task_id=task_id,
            type=type_,
            source=source,
            content=content,
            metadata=metadata,
            created_at=created_at,
        )

    return _create


@pytest.fixture
def memory_config() -> MemoryConfig:
    """
    Default MemoryConfig for tests.

    Returns a standard configuration suitable for most test scenarios.
    """
    return MemoryConfig(
        max_items_per_context=20,
        short_memory_ttl_ms=None,
        keyword_search_enabled=True,
        semantic_search_enabled=False,
    )


@pytest.fixture
def llm_gateway_config() -> LlmGatewayConfig:
    """
    Default LlmGatewayConfig for tests.

    Returns a mock configuration with test values.
    """
    return LlmGatewayConfig(
        base_url="http://localhost:8000/v1",
        token="test-token",
        project_id=67,
        default_timeout_ms=60000,
        max_retries=2,
        retry_delay_ms=1000,
    )


@pytest_asyncio.fixture
async def postgres_storage(clean_db) -> PostgresMemoryStorage:
    """
    Create an initialized PostgresMemoryStorage instance for integration tests.

    Uses a dedicated storage pool per test and ensures clean state via clean_db fixture.
    """
    dsn = _build_test_dsn()
    storage = PostgresMemoryStorage(dsn=dsn, min_size=1, max_size=3)
    await storage.initialize()
    try:
        yield storage
    finally:
        await storage.close()


@pytest.fixture
def mock_document_response():
    """
    Factory for creating mock document responses from chat_backend.

    Usage:
        response = mock_document_response(filename="test.md", content="# Test")
    """

    def _create(
        filename: str = "test.md",
        content: str = "# Test Document",
        version: int = 1,
    ) -> dict:
        return {
            "filename": filename,
            "content": content,
            "version": version,
        }

    return _create


@pytest.fixture
def sample_task_id() -> str:
    """Generate a unique task ID for each test (UUID format)."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_memory_id() -> str:
    """Generate a unique memory ID for each test (UUID format)."""
    return str(uuid.uuid4())