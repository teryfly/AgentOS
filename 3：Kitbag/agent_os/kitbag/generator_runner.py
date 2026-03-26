"""
ThreadPool-based generator consumer for generator-mode tools.

Responsibilities:
- Execute generator-mode tools in ThreadPoolExecutor
- Consume generator according to result_mapping.strategy
- Handle timeouts and exceptions

Supported strategies:
- collect_until_type: Iterate until message.type == terminal_type, return output_field
- last: Return last yielded item
- first: Return first yielded item
- all: Return list of all items
- attr_to_dict: Extract specified fields into dict

Design constraints:
- ThreadPool size configurable (default 4 workers)
- Timeout support (0 = no timeout)
- Generator exceptions caught and logged
- Cleanup on shutdown (wait for threads to complete)
"""

import logging
import concurrent.futures
from typing import Any, Callable

logger = logging.getLogger(__name__)


class GeneratorRunner:
    """
    ThreadPool-based generator consumer.
    
    Executes generator-mode tools in separate threads to avoid blocking
    the asyncio event loop.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize generator runner.
        
        Args:
            max_workers: ThreadPool size
        """
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def run(
        self,
        callable_fn: Callable,
        params: dict,
        result_mapping: dict,
        timeout_ms: int = 0,
    ) -> Any:
        """
        Run generator in thread pool and consume according to strategy.
        
        Args:
            callable_fn: Generator function to execute
            params: Parameters to pass to generator
            result_mapping: Strategy config (strategy, terminal_type, output_field, fields)
            timeout_ms: Timeout in milliseconds (0 = no timeout)
        
        Returns:
            Consumed result according to strategy
        
        Raises:
            TimeoutError: If timeout exceeded
            Exception: If generator raises exception
        """
        strategy = result_mapping.get("strategy", "last")
        timeout_secs = timeout_ms / 1000 if timeout_ms > 0 else None

        def task():
            # Execute generator and consume it within the thread pool
            generator = callable_fn(**params)
            
            if strategy == "collect_until_type":
                return self._collect_until_type(generator, result_mapping)
            elif strategy == "last":
                return self._collect_last(generator)
            elif strategy == "first":
                return self._collect_first(generator)
            elif strategy == "all":
                return self._collect_all(generator)
            elif strategy == "attr_to_dict":
                return self._attr_to_dict(generator, result_mapping.get("fields", []))
            else:
                raise ValueError(f"Unknown generator strategy: {strategy}")

        # Submit the entire consumption task to thread pool
        future = self._executor.submit(task)

        try:
            return future.result(timeout=timeout_secs)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Generator execution timed out after {timeout_ms}ms")

    def _collect_until_type(self, generator, result_mapping: dict):
        """
        Iterate until message.type == terminal_type, return output_field.
        """
        terminal_type = result_mapping.get("terminal_type")
        output_field = result_mapping.get("output_field")
        last_message = None

        try:
            for message in generator:
                last_message = message
                if isinstance(message, dict) and message.get("type") == terminal_type:
                    return message.get(output_field, message)
        except Exception as e:
            logger.error(f"Generator raised exception: {e}", exc_info=True)
            raise

        # No terminal type found, return last message or None
        if last_message is None:
            return None
        if isinstance(last_message, dict):
            return last_message.get(output_field, last_message)
        return last_message

    def _collect_last(self, generator):
        """Return last yielded item."""
        last = None
        for item in generator:
            last = item
        return last

    def _collect_first(self, generator):
        """Return first yielded item."""
        return next(generator, None)

    def _collect_all(self, generator):
        """Return list of all items."""
        return list(generator)

    def _attr_to_dict(self, generator, fields: list):
        """Extract specified fields from last message into dict."""
        last = None
        for item in generator:
            last = item
        if not last:
            return {}
        return {field: getattr(last, field, None) for field in fields}

    def shutdown(self, wait: bool = True):
        """Shutdown thread pool."""
        self._executor.shutdown(wait=wait)