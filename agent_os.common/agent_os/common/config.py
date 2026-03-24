"""agent_os/common/config.py - 公共配置模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RuntimeConfig:
    """
    AgentRuntime 运行时配置。

    max_step_depth 默认 50：
    编码自动化场景通常包含较多步骤和工具调用轮次，避免过早中断。
    """

    max_step_depth: int = 50
    poll_interval_ms: int = 500
    poll_enabled: bool = True


@dataclass
class MemoryConfig:
    """
    MemoryCenter 配置。

    max_items_per_context 默认 20：
    多 Actor 协作时上下文条目较多，降低关键信息被裁剪风险。
    """

    max_items_per_context: int = 20
    short_memory_ttl_ms: Optional[int] = None
    keyword_search_enabled: bool = True
    semantic_search_enabled: bool = False


@dataclass
class LlmGatewayConfig:
    """
    LlmGateway 连接配置。

    token 必须通过环境变量注入，禁止硬编码。
    """

    base_url: str
    token: str
    project_id: int
    default_timeout_ms: int = 60000
    max_retries: int = 2
    retry_delay_ms: int = 1000