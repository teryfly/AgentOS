"""LlmActor 与 GroupActor 类型层级与契约测试。"""

from __future__ import annotations

import asyncio

from agent_os.common import (
    Actor,
    ActorResponse,
    ActorResponseType,
    CollaborationStrategy,
    DeterministicActor,
    ExecutionContext,
    GroupActor,
    LlmActor,
    LlmConfig,
    Task,
    TaskStatus,
)


def _make_task() -> Task:
    """构造最小可执行任务。"""
    return Task(
        id="task-type-test",
        name="type test",
        description="verify actor type hierarchy",
        role="tester",
        status=TaskStatus.RUNNING,
    )


def _make_context() -> ExecutionContext:
    """构造最小执行上下文。"""
    return ExecutionContext(task_id="task-type-test", step_depth=1, max_step_depth=5)


def test_llm_actor_is_subclass_of_actor() -> None:
    """LlmActor 应继承自 Actor 基类。"""
    assert issubclass(LlmActor, Actor)


def test_llm_actor_base_act_raises_not_implemented_error() -> None:
    """LlmActor 基类未覆盖 act() 时应抛 NotImplementedError。"""
    actor = LlmActor()
    actor.name = "TestLlm"
    actor.role = "llm_test"
    actor.description = "Test LLM actor"
    actor.skills = []
    actor.allowed_tools = []
    actor.system_prompt = "test prompt"
    actor.llm_config = LlmConfig(model="test-model")
    actor._llm_gateway = None

    async def run() -> None:
        await actor.act(_make_task(), _make_context())

    try:
        asyncio.run(run())
    except NotImplementedError as err:
        assert "act() is not implemented" in str(err)
    else:
        raise AssertionError("LlmActor.act() should raise NotImplementedError")


def test_llm_actor_subclass_can_override_act() -> None:
    """LlmActor 子类覆盖 act() 后应正常工作。"""

    class CustomLlmActor(LlmActor):
        def __init__(self) -> None:
            self.name = "Custom"
            self.role = "custom_llm"
            self.description = "Custom LLM actor"
            self.skills = ["custom"]
            self.allowed_tools = []
            self.system_prompt = "custom prompt"
            self.llm_config = LlmConfig(model="custom-model", temperature=0.5)
            self._llm_gateway = None

        async def act(self, task: Task, context: ExecutionContext) -> ActorResponse:
            return ActorResponse(
                type=ActorResponseType.FINAL,
                content=f"llm:{task.id}",
            )

    actor = CustomLlmActor()

    async def run() -> ActorResponse:
        return await actor.act(_make_task(), _make_context())

    response = asyncio.run(run())
    assert response.type == ActorResponseType.FINAL
    assert response.content == "llm:task-type-test"


def test_group_actor_is_subclass_of_actor() -> None:
    """GroupActor 应继承自 Actor 基类。"""
    assert issubclass(GroupActor, Actor)


def test_group_actor_base_act_raises_not_implemented_error() -> None:
    """GroupActor 基类未覆盖 act() 时应抛 NotImplementedError。"""
    actor = GroupActor()
    actor.name = "TestGroup"
    actor.role = "group_test"
    actor.description = "Test group actor"
    actor.skills = []
    actor.allowed_tools = []
    actor.members = ["member1", "member2"]
    actor.strategy = CollaborationStrategy.SEQUENTIAL
    actor.max_rounds = 5
    actor.max_code_block_recovery = 3

    async def run() -> None:
        await actor.act(_make_task(), _make_context())

    try:
        asyncio.run(run())
    except NotImplementedError as err:
        assert "act() is not implemented" in str(err)
    else:
        raise AssertionError("GroupActor.act() should raise NotImplementedError")


def test_group_actor_subclass_can_override_act() -> None:
    """GroupActor 子类覆盖 act() 后应正常工作。"""

    class CustomGroupActor(GroupActor):
        def __init__(self) -> None:
            self.name = "CustomGroup"
            self.role = "custom_group"
            self.description = "Custom group actor"
            self.skills = ["orchestration"]
            self.allowed_tools = []
            self.members = ["coder", "reviewer"]
            self.strategy = CollaborationStrategy.ROUND_ROBIN
            self.max_rounds = 10
            self.max_code_block_recovery = 5

        async def act(self, task: Task, context: ExecutionContext) -> ActorResponse:
            return ActorResponse(
                type=ActorResponseType.CONTINUE,
                content={"next_member": self.members[0]},
            )

    actor = CustomGroupActor()

    async def run() -> ActorResponse:
        return await actor.act(_make_task(), _make_context())

    response = asyncio.run(run())
    assert response.type == ActorResponseType.CONTINUE
    assert response.content["next_member"] == "coder"


def test_all_actor_types_share_common_attributes() -> None:
    """所有 Actor 类型应声明共同的基础属性。"""
    common_attrs = ["name", "role", "description", "skills", "allowed_tools"]

    for actor_cls in [Actor, DeterministicActor, LlmActor, GroupActor]:
        for attr in common_attrs:
            assert hasattr(actor_cls, "__annotations__")
            assert attr in actor_cls.__annotations__, (
                f"{actor_cls.__name__} missing attribute: {attr}"
            )


def test_llm_actor_has_specific_attributes() -> None:
    """LlmActor 应声明特定属性。"""
    assert hasattr(LlmActor, "__annotations__")
    assert "system_prompt" in LlmActor.__annotations__
    assert "llm_config" in LlmActor.__annotations__
    assert "_llm_gateway" in LlmActor.__annotations__


def test_group_actor_has_specific_attributes() -> None:
    """GroupActor 应声明特定属性。"""
    assert hasattr(GroupActor, "__annotations__")
    assert "members" in GroupActor.__annotations__
    assert "strategy" in GroupActor.__annotations__
    assert "max_rounds" in GroupActor.__annotations__
    assert "max_code_block_recovery" in GroupActor.__annotations__