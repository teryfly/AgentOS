"""agent_os/common/enums.py - 公共枚举定义。"""

from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    WAITING_DEPENDENCY = "WAITING_DEPENDENCY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ActorResponseType(str, Enum):
    """Actor 响应动作类型。"""

    FINAL = "FINAL"
    TOOL_CALL = "TOOL_CALL"
    CREATE_TASK = "CREATE_TASK"
    WAIT_INPUT = "WAIT_INPUT"
    CONTINUE = "CONTINUE"


class MemoryType(str, Enum):
    """记忆类型。"""

    SHORT = "short"
    LONG = "long"
    SHARED = "shared"


class MemorySource(str, Enum):
    """记忆来源。"""

    ACTOR = "actor"
    TOOL = "tool"
    TASK = "task"
    SYSTEM = "system"


class ToolCategory(str, Enum):
    """工具分类。"""

    SYSTEM = "system"
    DATA = "data"
    AI = "ai"
    EXTERNAL = "external"
    CODE = "code"


class CollaborationStrategy(str, Enum):
    """协作策略。"""

    SEQUENTIAL = "sequential"
    ROUND_ROBIN = "round_robin"
    REVIEW_LOOP = "review_loop"