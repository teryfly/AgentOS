"""枚举与异常可用性测试。"""

from __future__ import annotations

from agent_os.common import (
    ActorDefinitionError,
    ActorNotFoundError,
    ActorResponseType,
    CircularDependencyError,
    CollaborationStrategy,
    ContextBuildError,
    DependencyNotFoundError,
    DuplicateActorError,
    DuplicateRefIdError,
    DuplicateToolError,
    GroupStateSerializationError,
    InvalidActorError,
    InvalidStatusTransitionError,
    InvalidTaskStateError,
    LlmGatewayError,
    LlmOutputParseError,
    MaxDepthExceededError,
    MemorySource,
    MemoryType,
    MetadataUpdateConflictError,
    PlanGenerationError,
    PlanParseError,
    RegistrationInconsistencyError,
    RuntimeStateUpdateConflictError,
    SemanticSearchNotEnabledError,
    TaskNotFoundError,
    TaskStatus,
    ToolCategory,
    ToolDefinitionError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolValidationError,
)


def test_enum_values_match_contract() -> None:
    """枚举值应与 CTD/使用说明约定一致。"""
    assert TaskStatus.PENDING.value == "PENDING"
    assert TaskStatus.WAITING_DEPENDENCY.value == "WAITING_DEPENDENCY"
    assert ActorResponseType.CREATE_TASK.value == "CREATE_TASK"
    assert MemoryType.SHARED.value == "shared"
    assert MemorySource.SYSTEM.value == "system"
    assert ToolCategory.CODE.value == "code"
    assert CollaborationStrategy.ROUND_ROBIN.value == "round_robin"


def test_all_exception_classes_are_raisable_and_catchable() -> None:
    """所有公共异常应可正常 raise/catch。"""
    exception_types = [
        TaskNotFoundError,
        InvalidStatusTransitionError,
        InvalidTaskStateError,
        MetadataUpdateConflictError,
        RuntimeStateUpdateConflictError,
        CircularDependencyError,
        DependencyNotFoundError,
        MaxDepthExceededError,
        DuplicateRefIdError,
        ActorNotFoundError,
        DuplicateActorError,
        InvalidActorError,
        ActorDefinitionError,
        ToolNotFoundError,
        ToolPermissionError,
        ToolValidationError,
        DuplicateToolError,
        ToolDefinitionError,
        ToolExecutionError,
        SemanticSearchNotEnabledError,
        PlanParseError,
        PlanGenerationError,
        GroupStateSerializationError,
        LlmGatewayError,
        LlmOutputParseError,
        RegistrationInconsistencyError,
        ContextBuildError,
    ]

    for exc_type in exception_types:
        try:
            raise exc_type("boom")
        except exc_type as err:
            assert str(err) == "boom"