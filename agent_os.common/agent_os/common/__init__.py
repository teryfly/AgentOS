"""
agent_os/common/__init__.py
公开 API 入口，使用显式导入确保可静态分析。
"""

from .enums import (
    ActorResponseType,
    CollaborationStrategy,
    MemorySource,
    MemoryType,
    TaskStatus,
    ToolCategory,
)
from .exceptions import (
    ActorDefinitionError,
    ActorNotFoundError,
    CircularDependencyError,
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
    MetadataUpdateConflictError,
    PlanGenerationError,
    PlanParseError,
    RegistrationInconsistencyError,
    RuntimeStateUpdateConflictError,
    SemanticSearchNotEnabledError,
    TaskNotFoundError,
    ToolDefinitionError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolValidationError,
)
from .interfaces import EventBus
from .event_bus import InMemoryEventBus
from .config import LlmGatewayConfig, MemoryConfig, RuntimeConfig
from .models import (
    Actor,
    ActorMeta,
    ActorResponse,
    DeterministicActor,
    ExecutionContext,
    GroupActor,             # v1.1 新增
    GroupState,
    GroupTurn,
    LlmActor,               # v1.1 新增
    LlmConfig,
    MemoryContext,
    MemoryItem,
    ModelPoolEntry,         # v1.1 新增
    ParameterDef,
    Plan,
    PlannedTask,
    RoleRouterConfig,
    RouterRule,
    Task,
    TaskBatchItem,
    TaskResult,
    TaskRuntimeState,
    ToolCall,
    ToolCapabilitySummary,
    ToolResult,
    ToolSchema,
)
from .events import (
    ConversationAssigned,   # v1.1 新增
    StepProgress,
    TaskCompleted,
    TaskCreated,
    TaskFailed,
    TaskResumed,
    TaskStarted,
    TaskUnblocked,
    TaskWaitingDependency,
    TaskWaitingInput,
)

__all__ = [
    # enums
    "TaskStatus", "ActorResponseType", "MemoryType", "MemorySource",
    "ToolCategory", "CollaborationStrategy",
    # exceptions
    "TaskNotFoundError", "InvalidStatusTransitionError", "InvalidTaskStateError",
    "MetadataUpdateConflictError", "RuntimeStateUpdateConflictError",
    "CircularDependencyError", "DependencyNotFoundError", "MaxDepthExceededError",
    "DuplicateRefIdError",
    "ActorNotFoundError", "DuplicateActorError", "InvalidActorError", "ActorDefinitionError",
    "ToolNotFoundError", "ToolPermissionError", "ToolValidationError",
    "DuplicateToolError", "ToolDefinitionError", "ToolExecutionError",
    "SemanticSearchNotEnabledError",
    "PlanParseError", "PlanGenerationError",
    "GroupStateSerializationError",
    "LlmGatewayError", "LlmOutputParseError",
    "RegistrationInconsistencyError",
    "ContextBuildError",
    # interfaces
    "EventBus",
    "InMemoryEventBus",
    # config
    "RuntimeConfig", "MemoryConfig", "LlmGatewayConfig",
    # models — Actor 基类层级
    "Actor",
    "DeterministicActor",
    "LlmActor",             # v1.1 新增
    "GroupActor",           # v1.1 新增
    # models — 任务
    "TaskResult", "Task", "TaskRuntimeState", "TaskBatchItem",
    "ExecutionContext", "ActorResponse",
    # models — 工具
    "ParameterDef", "ToolSchema", "ToolCall", "ToolResult",
    # models — 记忆
    "MemoryItem", "MemoryContext",
    # models — 规划
    "PlannedTask", "Plan", "RouterRule", "RoleRouterConfig",
    # models — LLM
    "LlmConfig",
    # models — 协作
    "GroupTurn", "GroupState",
    # models — 能力描述
    "ToolCapabilitySummary",
    "ModelPoolEntry",       # v1.1 新增
    "ActorMeta",
    # events
    "TaskCreated", "TaskStarted", "TaskCompleted", "TaskFailed",
    "TaskWaitingInput", "TaskWaitingDependency", "TaskUnblocked", "TaskResumed",
    "StepProgress",
    "ConversationAssigned", # v1.1 新增
]