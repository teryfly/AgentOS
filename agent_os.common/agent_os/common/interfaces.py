"""agent_os/common/interfaces.py — 抽象接口，不包含任何具体实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Type


class EventBus(ABC):
    """事件总线抽象接口。"""

    @abstractmethod
    async def publish(self, event: Any) -> None:
        """发布事件，依次调用所有订阅者。"""
        raise NotImplementedError

    @abstractmethod
    def subscribe(
        self,
        event_type: Type,
        handler: Callable[[Any], Awaitable[None]],
    ) -> None:
        """订阅指定类型事件。"""
        raise NotImplementedError