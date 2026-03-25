"""
Configuration factory functions for MemoryCenter.

This module provides factory functions to create MemoryCenter instances
from environment variables, reducing boilerplate in application code.
"""

import os
from typing import Optional

import httpx

from agent_os.common import LlmGatewayConfig, MemoryConfig

from .memory_center import MemoryCenter
from .storage import PostgresMemoryStorage


def create_memory_center_from_env(
    dsn: Optional[str] = None,
    http_client: Optional[httpx.AsyncClient] = None,
) -> MemoryCenter:
    """
    Create MemoryCenter instance using environment variables.
    
    Required environment variables:
      - DB_HOST: PostgreSQL host (default: localhost)
      - DB_PORT: PostgreSQL port (default: 5432)
      - DB_NAME: Database name (required)
      - DB_USER: Database user (required)
      - DB_PASSWORD: Database password (required)
      - CHAT_BACKEND_URL: chat_backend base URL (required)
      - API_KEY: Bearer token for chat_backend (required)
      - CHAT_BACKEND_PROJECT_ID: Project ID (required)
    
    Optional environment variables:
      - MEMORY_MAX_ITEMS: Max items per context (default: 20)
      - MEMORY_SEMANTIC_ENABLED: Enable semantic search (default: false)
    
    Args:
        dsn: Optional PostgreSQL DSN. If None, builds from env vars.
        http_client: Optional HTTP client for document queries.
                    If None, creates a new one.
    
    Returns:
        MemoryCenter instance (storage must be initialized separately)
        
    Raises:
        ValueError: If required environment variables are missing
        
    Usage:
        memory_center = create_memory_center_from_env()
        await memory_center._storage.initialize()
        
        # Use memory_center...
        
        await memory_center.close()
    """
    _validate_env_vars()
    
    # Build MemoryConfig from environment
    memory_config = MemoryConfig(
        max_items_per_context=int(os.getenv("MEMORY_MAX_ITEMS", "20")),
        short_memory_ttl_ms=None,  # Not used in MVP
        keyword_search_enabled=True,
        semantic_search_enabled=_parse_bool(
            os.getenv("MEMORY_SEMANTIC_ENABLED", "false")
        ),
    )
    
    # Build LlmGatewayConfig for document service
    llm_config = LlmGatewayConfig(
        base_url=os.getenv("CHAT_BACKEND_URL", ""),
        token=os.getenv("API_KEY", ""),
        project_id=int(os.getenv("CHAT_BACKEND_PROJECT_ID", "0")),
        default_timeout_ms=int(os.getenv("CHAT_BACKEND_TIMEOUT_MS", "60000")),
        max_retries=int(os.getenv("CHAT_BACKEND_MAX_RETRIES", "2")),
        retry_delay_ms=int(os.getenv("CHAT_BACKEND_RETRY_DELAY_MS", "1000")),
    )
    
    # Create storage
    storage = PostgresMemoryStorage(dsn=dsn)
    
    # Create and return MemoryCenter
    return MemoryCenter(
        storage=storage,
        config=memory_config,
        llm_gateway_config=llm_config,
        http_client=http_client,
    )


def _validate_env_vars() -> None:
    """
    Validate that required environment variables are present.
    
    Raises:
        ValueError: If any required variable is missing
    """
    required = [
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "CHAT_BACKEND_URL",
        "API_KEY",
        "CHAT_BACKEND_PROJECT_ID",
    ]
    
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


def _parse_bool(value: str) -> bool:
    """
    Parse boolean value from string.
    
    Args:
        value: String value (case-insensitive)
        
    Returns:
        True if value is "true", "yes", "1", etc.
        False otherwise
    """
    return value.lower() in ("true", "yes", "1", "on")