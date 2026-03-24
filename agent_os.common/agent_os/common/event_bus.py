"""agent_os/common/event_bus.py — InMemoryEventBus 具体实现。"""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Awaitable, Callable, Dict, List, Type

from .interfaces import EventBus

logger = logging.getLogger(__name__)


class InMemoryEventBus(EventBus):
    """
    基于内存的事件总线实现。

    行为约定：
    - publish 按订阅顺序串行 await 各 handler
    - 单个 handler 抛出异常时，捕获并记录 warning，继续调用后续 handler
    - 使用锁保护订阅表读写，确保并发场景下快照一致性
    """

    def __init__(self) -> None:
        self._handlers: Dict[Type, List[Callable[[Any], Awaitable[None]]]] = {}
        self._lock = RLock()

    def subscribe(
        self,
        event_type: Type,
        handler: Callable[[Any], Awaitable[None]],
    ) -> None:
        """订阅指定事件类型，按调用顺序追加处理器。"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        """
        发布事件并按订阅顺序执行处理器。

        注意：
        - 仅分发完全匹配 type(event) 的处理器
        - 单个处理器失败不会中断后续处理器
        """
        with self._lock:
            handlers = list(self._handlers.get(type(event), []))

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "InMemoryEventBus: handler %s raised an exception for event %s: %s",
                    getattr(handler, "__qualname__", repr(handler)),
                    type(event).__name__,
                    exc,
                    exc_info=True,
                )