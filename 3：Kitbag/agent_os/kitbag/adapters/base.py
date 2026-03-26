"""
Protocol adapter abstract base class.

Responsibilities:
- Define interface for building Tool instances from YAML config
- Each concrete adapter handles one protocol (python/http/subprocess)

Design constraints:
- Stateless (no instance variables retained between calls)
- Receives tool_configs (list of per-tool configs) + defaults (suite-level shared config)
- Returns list of Tool instances
"""

from abc import ABC, abstractmethod
from ..tool_base import Tool


class ProtocolAdapter(ABC):
    """
    Abstract base class for protocol adapters.
    
    Protocol adapters convert YAML tool definitions into Tool instances.
    Each adapter handles one protocol (python/http/subprocess/grpc/mcp).
    """

    @abstractmethod
    def build_tools(self, tool_configs: list[dict], defaults: dict) -> list[Tool]:
        """
        Build Tool instances from YAML configuration.
        
        Args:
            tool_configs: List of per-tool config dicts
            defaults: Suite-level shared config (e.g., python_defaults)
        
        Returns:
            List of Tool instances
        
        Raises:
            Exception: On configuration error (caught by YamlToolLoader)
        """
        raise NotImplementedError