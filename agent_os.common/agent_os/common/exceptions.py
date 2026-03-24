"""agent_os/common/exceptions.py - 公共异常定义。"""


# TaskCenter 异常
class TaskNotFoundError(Exception):
    """任务不存在。"""


class InvalidStatusTransitionError(Exception):
    """状态流转非法，或 resume_task CAS 失败。"""


class InvalidTaskStateError(Exception):
    """在非法状态下调用 update_task_metadata / update_task_runtime_state。"""


class MetadataUpdateConflictError(Exception):
    """update_task_metadata 乐观锁重试耗尽。"""


class RuntimeStateUpdateConflictError(Exception):
    """update_task_runtime_state 乐观锁重试耗尽。"""


class CircularDependencyError(Exception):
    """检测到循环依赖。"""


class DependencyNotFoundError(Exception):
    """依赖的 task_id 不存在。"""


class MaxDepthExceededError(Exception):
    """TaskGraph 嵌套深度超过限制。"""


class DuplicateRefIdError(Exception):
    """批量创建时 ref_id 重复。"""


# ActorRegistry 异常
class ActorNotFoundError(Exception):
    """Actor 未注册。"""


class DuplicateActorError(Exception):
    """Actor 重复注册。"""


class InvalidActorError(Exception):
    """Actor 未实现 act() 方法。"""


class ActorDefinitionError(Exception):
    """Actor YAML 定义格式错误（加载阶段）。"""


# Kitbag 异常
class ToolNotFoundError(Exception):
    """工具不存在。"""


class ToolPermissionError(Exception):
    """高危工具 allowed_roles 校验失败（仅内部使用，对外转为 ToolResult）。"""


class ToolValidationError(Exception):
    """工具参数校验失败。"""


class DuplicateToolError(Exception):
    """工具重复注册。"""


class ToolDefinitionError(Exception):
    """工具 YAML 定义格式错误（加载阶段）。"""


class ToolExecutionError(Exception):
    """工具执行内部错误（如 async 工具不支持）。"""


# MemoryCenter 异常
class SemanticSearchNotEnabledError(Exception):
    """语义检索未启用，通过 MemoryConfig 显式开启。"""


# PlannerActor 异常
class PlanParseError(Exception):
    """Plan JSON 解析失败。"""


class PlanGenerationError(Exception):
    """Plan 生成失败（LLM 调用或解析失败）。"""


# GroupActor 异常
class GroupStateSerializationError(Exception):
    """GroupState 序列化/反序列化失败。"""


# LlmGateway 异常
class LlmGatewayError(Exception):
    """chat_backend 调用失败（网络/HTTP 错误）。"""


class LlmOutputParseError(Exception):
    """LLM 输出结构错误，无法解析为有效 ActorResponse。"""


# RegistrationCoordinator 异常
class RegistrationInconsistencyError(Exception):
    """启动时跨模块引用完整性校验失败，系统拒绝启动。"""


# ContextBuilder 异常
class ContextBuildError(Exception):
    """ContextBuilder 构建 ExecutionContext 失败。"""