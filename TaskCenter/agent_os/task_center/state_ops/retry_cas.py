"""
Generic optimistic lock retry mechanism.

Provides reusable CAS retry logic for metadata and runtime state updates.
"""
import logging
from typing import Callable, Awaitable
from ..storage.interfaces import VersionConflict

logger = logging.getLogger(__name__)


async def retry_optimistic(
    operation_fn: Callable[[], Awaitable[None]],
    max_retries: int,
    conflict_exception_type: type
) -> None:
    """
    Execute operation with automatic CAS retry.
    
    Args:
        operation_fn: Async function that raises VersionConflict on CAS failure
        max_retries: Maximum retry attempts
        conflict_exception_type: Exception type to raise on exhaustion
        
    Raises:
        conflict_exception_type: Retries exhausted
    """
    for attempt in range(max_retries):
        try:
            await operation_fn()
            return
        except VersionConflict as e:
            if attempt == max_retries - 1:
                logger.warning(f"[TaskCenter | retry_optimistic] Retry exhausted after {max_retries} attempts")
                raise conflict_exception_type(f"CAS conflict after {max_retries} retries") from e
            
            logger.debug(f"[TaskCenter | retry_optimistic] CAS conflict on attempt {attempt + 1}, retrying...")