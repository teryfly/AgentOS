"""
YAML tool definition loader.

Responsibilities:
- Recursively scan directory for *.yaml files
- Skip files starting with underscore
- Parse multi-document YAML (--- separator)
- Apply environment variable substitution
- Dispatch to ProtocolAdapter by protocol field
- Register built tools into Kitbag
- Isolate single-file failures

Design constraints:
- Single file failure logged but does not abort overall loading
- Unknown protocol logged as warning, file skipped
- Duplicate tool names caught by Kitbag.register()
"""

import logging
import yaml
from pathlib import Path
from .kitbag import Kitbag
from .env_utils import substitute_env_vars
from .adapters import (
    PythonProtocolAdapter,
    HttpProtocolAdapter,
    SubprocessProtocolAdapter,
)

logger = logging.getLogger(__name__)


class YamlToolLoader:
    """
    YAML tool definition loader.
    
    Recursively scans directory and loads tool definitions from YAML files.
    """

    PROTOCOL_ADAPTERS = {
        "python": PythonProtocolAdapter,
        "http": HttpProtocolAdapter,
        "subprocess": SubprocessProtocolAdapter,
    }

    def load_from_dir(self, kitbag: Kitbag, dir_path: str) -> None:
        """
        Recursively scan directory and load all YAML tool definitions.
        
        Behavior:
        - *.yaml files loaded
        - _*.yaml files skipped
        - Multi-document YAML supported
        - Single file failures isolated (logged, others continue)
        
        Args:
            kitbag: Kitbag instance to register tools into
            dir_path: Directory path to scan
        """
        base_path = Path(dir_path)
        if not base_path.exists():
            logger.warning(f"Tool directory '{dir_path}' does not exist")
            return

        yaml_files = list(base_path.rglob("*.yaml"))
        logger.info(f"Found {len(yaml_files)} YAML files in '{dir_path}'")

        for file_path in yaml_files:
            # Skip underscore-prefixed files
            if file_path.name.startswith("_"):
                logger.debug(f"Skipping file: {file_path}")
                continue

            try:
                self._load_file(kitbag, file_path)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}", exc_info=True)
                # Continue loading other files

    def _load_file(self, kitbag: Kitbag, file_path: Path) -> None:
        """
        Load single YAML file (may contain multiple documents).
        
        Args:
            kitbag: Kitbag instance
            file_path: YAML file path
        """
        with open(file_path, "r", encoding="utf-8") as f:
            documents = list(yaml.safe_load_all(f))

        for doc in documents:
            if not doc:
                continue

            # Apply env-var substitution
            doc = substitute_env_vars(doc)

            # Extract protocol and select adapter
            protocol = doc.get("protocol")
            if not protocol:
                logger.error(f"Missing 'protocol' field in {file_path}")
                continue

            adapter_class = self.PROTOCOL_ADAPTERS.get(protocol)
            if not adapter_class:
                logger.warning(f"Unknown protocol '{protocol}' in {file_path}")
                continue

            # Build tools via adapter
            adapter = adapter_class()
            tool_configs = doc.get("tools", [])
            defaults = self._extract_defaults(doc, protocol)

            try:
                tools = adapter.build_tools(tool_configs, defaults)
            except Exception as e:
                logger.error(f"Adapter failed to build tools from {file_path}: {e}")
                continue

            # Register each tool
            for tool in tools:
                try:
                    # Inject generator_runner for PythonTool if needed
                    if hasattr(tool, "_generator_runner") and tool._generator_runner is None:
                        tool._generator_runner = kitbag.get_generator_runner()

                    kitbag.register(tool)
                    logger.info(f"Registered tool: {tool.name} (protocol={protocol})")
                except Exception as e:
                    logger.error(f"Failed to register tool {tool.name}: {e}")

    def _extract_defaults(self, doc: dict, protocol: str) -> dict:
        """
        Extract protocol-specific defaults.
        
        Args:
            doc: YAML document
            protocol: Protocol name
        
        Returns:
            Protocol defaults dict
        
        Examples:
            >>> doc = {"python_defaults": {...}}
            >>> _extract_defaults(doc, "python")
            {...}
        """
        key = f"{protocol}_defaults"
        return doc.get(key, {})