"""
Serialization helpers for converting between MemoryItem and database rows.

This module handles JSON serialization of the content field and enum conversion.
All functions are pure (no I/O) and easily testable.
"""

import json
from typing import Any
import uuid

from agent_os.common import MemoryItem, MemoryType, MemorySource


def memory_item_to_row(item: MemoryItem) -> dict[str, Any]:
    """
    Convert MemoryItem to dictionary for database insertion.
    
    Args:
        item: MemoryItem instance to convert
        
    Returns:
        Dictionary with keys matching database columns:
        - id: UUID string
        - task_id: UUID string
        - type: MemoryType enum value (string)
        - source: MemorySource enum value (string)
        - content: JSON-serialized string
        - metadata: JSON-serialized string (for JSONB column)
        - created_at: Unix timestamp in milliseconds
        
    Note:
        Both content and metadata fields are JSON-serialized to strings.
        PostgreSQL will cast the JSON string to JSONB type automatically.
    """
    return {
        "id": item.id,
        "task_id": item.task_id,
        "type": item.type.value,
        "source": item.source.value,
        "content": json.dumps(item.content, ensure_ascii=False),
        "metadata": json.dumps(item.metadata, ensure_ascii=False),
        "created_at": item.created_at,
    }


def row_to_memory_item(row: dict[str, Any]) -> MemoryItem:
    """
    Convert database row to MemoryItem instance.
    
    Args:
        row: Dictionary with keys matching database columns
        
    Returns:
        MemoryItem instance
        
    Raises:
        json.JSONDecodeError: If content or metadata field is not valid JSON
        ValueError: If type/source enum values are invalid
        
    Note:
        Both content and metadata fields are deserialized from JSON strings.
        If metadata is None or empty string, defaults to empty dict.
        UUID fields are converted from UUID objects to strings.
    """
    # Convert UUID objects to strings if needed
    item_id = row["id"]
    if isinstance(item_id, uuid.UUID):
        item_id = str(item_id)
    
    task_id = row["task_id"]
    if isinstance(task_id, uuid.UUID):
        task_id = str(task_id)
    
    # Deserialize metadata, handling None/empty cases
    metadata_raw = row.get("metadata")
    if metadata_raw is None or metadata_raw == "":
        metadata = {}
    elif isinstance(metadata_raw, str):
        metadata = json.loads(metadata_raw)
    else:
        # Already a dict (from asyncpg JSONB auto-conversion in some cases)
        metadata = metadata_raw
    
    return MemoryItem(
        id=item_id,
        task_id=task_id,
        type=MemoryType(row["type"]),
        source=MemorySource(row["source"]),
        content=json.loads(row["content"]),
        metadata=metadata,
        created_at=row["created_at"],
    )


def batch_to_rows(items: list[MemoryItem]) -> list[dict[str, Any]]:
    """
    Convert list of MemoryItem to list of row dictionaries.
    
    Args:
        items: List of MemoryItem instances
        
    Returns:
        List of row dictionaries suitable for batch insertion
        
    Note:
        Used for batch write operations to avoid repeated serialization logic.
    """
    return [memory_item_to_row(item) for item in items]


def rows_to_batch(rows: list[dict[str, Any]]) -> list[MemoryItem]:
    """
    Convert list of database rows to list of MemoryItem instances.
    
    Args:
        rows: List of row dictionaries from database query
        
    Returns:
        List of MemoryItem instances
        
    Raises:
        json.JSONDecodeError: If any content or metadata field is invalid JSON
        ValueError: If any type/source enum value is invalid
        
    Note:
        Used for batch read operations. Partial failures in individual
        row conversions are not caught here - caller should handle.
    """
    return [row_to_memory_item(row) for row in rows]