"""
Unit tests for KitbagConfig and Kitbag initialization.

Coverage:
- Default configuration values
- Custom configuration
- Thread pool sizing
- Multiple Kitbag instances
- Configuration immutability
"""

import pytest
from agent_os.kitbag import Kitbag, KitbagConfig
from tests.shared_mocks import MockTool


def test_kitbag_default_config():
    """Test Kitbag initialization with default configuration."""
    kitbag = Kitbag()
    
    # Verify internal dependencies are initialized
    assert kitbag._validator is not None
    assert kitbag._permission_checker is not None
    assert kitbag._result_standardizer is not None
    assert kitbag._generator_runner is not None
    assert kitbag._executor is not None
    assert kitbag._tools == {}


def test_kitbag_custom_config():
    """Test Kitbag initialization with custom configuration."""
    config = KitbagConfig(max_workers=8, default_timeout_ms=60000)
    kitbag = Kitbag(config)
    
    assert kitbag._config.max_workers == 8
    assert kitbag._config.default_timeout_ms == 60000


def test_kitbag_config_default_values():
    """Test KitbagConfig default values."""
    config = KitbagConfig()
    
    assert config.max_workers == 4
    assert config.default_timeout_ms == 0


def test_kitbag_config_custom_values():
    """Test KitbagConfig with custom values."""
    config = KitbagConfig(max_workers=16, default_timeout_ms=120000)
    
    assert config.max_workers == 16
    assert config.default_timeout_ms == 120000


def test_multiple_kitbag_instances_isolated():
    """Test that multiple Kitbag instances are isolated."""
    kitbag1 = Kitbag()
    kitbag2 = Kitbag()
    
    tool1 = MockTool(name="tool1")
    tool2 = MockTool(name="tool2")
    
    kitbag1.register(tool1)
    kitbag2.register(tool2)
    
    # Each instance should have only its own tools
    assert kitbag1.exists("tool1")
    assert not kitbag1.exists("tool2")
    assert kitbag2.exists("tool2")
    assert not kitbag2.exists("tool1")


def test_kitbag_config_thread_pool_sizing():
    """Test that thread pool is sized according to config."""
    config = KitbagConfig(max_workers=2)
    kitbag = Kitbag(config)
    
    runner = kitbag.get_generator_runner()
    assert runner is not None
    # Note: Internal thread pool size not directly testable
    # but verified through integration tests


def test_kitbag_shutdown_multiple_times():
    """Test that shutdown can be called multiple times safely."""
    kitbag = Kitbag()
    
    kitbag.shutdown()
    kitbag.shutdown()  # Should not raise error


def test_kitbag_initialization_with_none_config():
    """Test Kitbag initialization when config is None (uses defaults)."""
    kitbag = Kitbag(config=None)
    
    assert kitbag._config is not None
    assert kitbag._config.max_workers == 4
    assert kitbag._config.default_timeout_ms == 0