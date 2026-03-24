"""InMemoryEventBus 行为测试。"""

from __future__ import annotations

import asyncio
from typing import List

from agent_os.common import InMemoryEventBus, TaskCreated, TaskStatus


def test_event_bus_publish_calls_handlers_in_subscription_order() -> None:
    """发布事件后应按订阅顺序调用处理器。"""
    bus = InMemoryEventBus()
    called: List[str] = []

    async def handler_a(event: TaskCreated) -> None:
        called.append(f"a:{event.task_id}")

    async def handler_b(event: TaskCreated) -> None:
        called.append(f"b:{event.task_id}")

    bus.subscribe(TaskCreated, handler_a)
    bus.subscribe(TaskCreated, handler_b)

    async def run() -> None:
        await bus.publish(
            TaskCreated(
                task_id="task-order",
                name="demo",
                role="coder",
                status=TaskStatus.PENDING,
            )
        )

    asyncio.run(run())
    assert called == ["a:task-order", "b:task-order"]


def test_event_bus_handler_exception_is_isolated() -> None:
    """单个处理器抛异常不应阻断后续处理器。"""
    bus = InMemoryEventBus()
    called: List[str] = []

    async def handler_fail(event: TaskCreated) -> None:
        called.append("fail")
        raise RuntimeError("expected")

    async def handler_ok(event: TaskCreated) -> None:
        called.append("ok")

    bus.subscribe(TaskCreated, handler_fail)
    bus.subscribe(TaskCreated, handler_ok)

    async def run() -> None:
        await bus.publish(
            TaskCreated(
                task_id="task-isolation",
                name="demo",
                role="coder",
                status=TaskStatus.PENDING,
            )
        )

    asyncio.run(run())
    assert called == ["fail", "ok"]


def test_event_bus_duplicate_subscription_calls_handler_multiple_times() -> None:
    """重复订阅同一处理器应触发多次调用。"""
    bus = InMemoryEventBus()
    called: List[str] = []

    async def handler(event: TaskCreated) -> None:
        called.append(event.task_id)

    bus.subscribe(TaskCreated, handler)
    bus.subscribe(TaskCreated, handler)

    async def run() -> None:
        await bus.publish(
            TaskCreated(
                task_id="task-dup",
                name="demo",
                role="coder",
                status=TaskStatus.PENDING,
            )
        )

    asyncio.run(run())
    assert called == ["task-dup", "task-dup"]