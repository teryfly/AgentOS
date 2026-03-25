"""
Async testing utilities.

Helpers for concurrent test scenarios.
"""
import asyncio
from typing import Callable, Awaitable, Any, List


async def run_concurrent(tasks: List[Callable[[], Awaitable[Any]]]) -> List[Any]:
    """
    Run multiple async tasks concurrently.
    
    Args:
        tasks: List of async callables
        
    Returns:
        List of results (or exceptions)
    """
    results = await asyncio.gather(*[task() for task in tasks], return_exceptions=True)
    return results


async def run_concurrent_with_delay(
    tasks: List[Callable[[], Awaitable[Any]]],
    delay_ms: int = 10
) -> List[Any]:
    """
    Run tasks with small delay between starts.
    
    Useful for testing race conditions.
    """
    async def delayed_task(task, delay):
        await asyncio.sleep(delay / 1000)
        return await task()
    
    results = await asyncio.gather(
        *[delayed_task(task, i * delay_ms) for i, task in enumerate(tasks)],
        return_exceptions=True
    )
    return results


def count_exceptions(results: List[Any], exception_type: type) -> int:
    """Count occurrences of specific exception type in results."""
    return sum(1 for r in results if isinstance(r, exception_type))


def count_successes(results: List[Any]) -> int:
    """Count non-exception results."""
    return sum(1 for r in results if not isinstance(r, Exception))