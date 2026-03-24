"""Actor / DeterministicActor 契约测试。"""

from __future__ import annotations

import asyncio

from agent_os.common import (
    Actor,
    ActorResponse,
    ActorResponseType,
    DeterministicActor,
    ExecutionContext,
    Task,
    TaskStatus,
)


def _make_task() -> Task:
    """构造最小可执行任务。"""
    return Task(
        id="task-actor",
        name="actor test",
        description="verify actor contract",
        role="tester",
        status=TaskStatus.RUNNING,
    )


def _make_context() -> ExecutionContext:
    """构造最小执行上下文。"""
    return ExecutionContext(task_id="task-actor", step_depth=1, max_step_depth=5)


def test_actor_base_act_raises_not_implemented_error() -> None:
    """直接使用 Actor 基类调用 act 应抛 NotImplementedError。"""
    actor = Actor()

    async def run() -> None:
        await actor.act(_make_task(), _make_context())

    try:
        asyncio.run(run())
    except NotImplementedError:
        assert True
    else:
        raise AssertionError("Actor.act() should raise NotImplementedError")


def test_deterministic_actor_subclass_override_act_works() -> None:
    """DeterministicActor 子类覆盖 act 后应正常工作。"""

    class EchoDeterministicActor(DeterministicActor):
        name = "Echo"
        role = "echo"
        description = "Echo actor"
        skills = ["echo"]
        allowed_tools = []

        async def act(self, task: Task, context: ExecutionContext) -> ActorResponse:
            return ActorResponse(
                type=ActorResponseType.FINAL,
                content=f"{task.id}@{context.step_depth}",
            )

    actor = EchoDeterministicActor()

    async def run() -> ActorResponse:
        return await actor.act(_make_task(), _make_context())

    response = asyncio.run(run())
    assert response.type == ActorResponseType.FINAL
    assert response.content == "task-actor@1"