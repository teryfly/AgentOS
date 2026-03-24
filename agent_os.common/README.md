# agent-os-common

`agent-os-common` 是 Agent OS 的公共基础包，提供共享数据模型、枚举、异常、事件、接口和配置类，供 `task_center`、`agent_runtime`、`memory_center` 等模块统一复用。

## 安装

```bash
pip install agent-os-common
```

或在本地源码目录安装：

```bash
pip install .
```

## 命名空间包说明

本项目采用 PEP 420 命名空间包：
- `agent_os/` 目录下 **不包含** `__init__.py`
- 可与其他独立分发包（如 `agent_os.task_center`）并行安装

## 快速使用

```python
from agent_os.common import (
    Task,
    TaskStatus,
    Actor,
    EventBus,
    InMemoryEventBus,
    TaskCreated,
    StepProgress,
    RuntimeConfig,
    MemoryConfig,
    LlmGatewayConfig,
)
```

## 主要能力

- 统一领域枚举（任务状态、响应类型、工具分类等）
- 统一异常体系（任务、Actor、工具、LLM、注册校验等）
- 统一事件契约（TaskCenter 生命周期 + AgentRuntime 进度）
- 统一核心模型（Task、ToolResult、MemoryItem、GroupState 等）
- 抽象事件总线接口 + 内存事件总线实现
- 配置模型集中管理
- PEP 561 typed package（内置 `py.typed`）

## 事件总线示例

```python
import asyncio
from agent_os.common import InMemoryEventBus, TaskCreated, TaskStatus

async def main() -> None:
    bus = InMemoryEventBus()

    async def on_task_created(event: TaskCreated) -> None:
        print(f"created: {event.task_id} {event.status}")

    bus.subscribe(TaskCreated, on_task_created)
    await bus.publish(
        TaskCreated(
            task_id="task-001",
            name="demo",
            role="coder",
            status=TaskStatus.PENDING,
        )
    )

asyncio.run(main())
```

## 导出 API

所有公共能力均可从包级导入：

```python
from agent_os.common import *
```

推荐显式导入：

```python
from agent_os.common import Task, TaskCreated, InMemoryEventBus
```
