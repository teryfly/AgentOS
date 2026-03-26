"""
Shared test fixtures for Kitbag module.

Provides common fixtures used across unit and integration tests.
"""

import pytest
from agent_os.common import ToolCall
from agent_os.kitbag import Kitbag, KitbagConfig
from tests.shared_mocks import MockTool, HighRiskMockTool


@pytest.fixture
def kitbag():
    """Create Kitbag instance for testing."""
    return Kitbag(KitbagConfig(max_workers=2))


@pytest.fixture
def mock_tool():
    """Create mock tool instance."""
    return MockTool()


@pytest.fixture
def high_risk_tool():
    """Create high-risk mock tool instance."""
    return HighRiskMockTool()


@pytest.fixture
def registered_kitbag(kitbag, mock_tool):
    """Create Kitbag with registered mock tool."""
    kitbag.register(mock_tool)
    return kitbag


@pytest.fixture
def sample_tool_call():
    """Create sample ToolCall for testing."""
    return ToolCall(name="mock_tool", params={"param1": "test"}, caller_role="user")