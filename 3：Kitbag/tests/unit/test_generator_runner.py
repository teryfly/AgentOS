"""
Unit tests for GeneratorRunner.
"""

import pytest
import time
from agent_os.kitbag.generator_runner import GeneratorRunner


@pytest.fixture
def runner():
    """Create generator runner instance."""
    return GeneratorRunner(max_workers=2)


def simple_generator(**params):
    """Simple generator for testing."""
    for i in range(5):
        yield {"index": i, "value": params.get("value", "default")}


def terminal_type_generator(**params):
    """Generator with terminal type message."""
    yield {"type": "progress", "data": "step 1"}
    yield {"type": "progress", "data": "step 2"}
    yield {"type": "summary", "data": "final result"}
    yield {"type": "ignored", "data": "not reached"}


def failing_generator(**params):
    """Generator that raises exception."""
    yield {"value": 1}
    raise RuntimeError("Generator failed")


def test_run_collect_last(runner):
    """Test collect last strategy."""
    result = runner.run(simple_generator, {"value": "test"}, {"strategy": "last"})
    assert result["index"] == 4
    assert result["value"] == "test"


def test_run_collect_first(runner):
    """Test collect first strategy."""
    result = runner.run(simple_generator, {"value": "test"}, {"strategy": "first"})
    assert result["index"] == 0


def test_run_collect_all(runner):
    """Test collect all strategy."""
    result = runner.run(simple_generator, {"value": "test"}, {"strategy": "all"})
    assert len(result) == 5
    assert all("index" in item for item in result)


def test_run_collect_until_type(runner):
    """Test collect until type strategy."""
    result = runner.run(
        terminal_type_generator,
        {},
        {"strategy": "collect_until_type", "terminal_type": "summary", "output_field": "data"},
    )
    assert result == "final result"


def test_run_collect_until_type_not_found(runner):
    """Test collect until type when terminal type not found."""
    result = runner.run(
        simple_generator,
        {},
        {"strategy": "collect_until_type", "terminal_type": "missing", "output_field": "value"},
    )
    # Should return last message's output_field
    assert result == "default"


def test_run_timeout(runner):
    """Test timeout handling."""
    
    def slow_generator(**params):
        time.sleep(2)
        yield {"value": "done"}
    
    with pytest.raises(TimeoutError):
        runner.run(slow_generator, {}, {"strategy": "last"}, timeout_ms=500)


def test_run_generator_exception(runner):
    """Test that generator exceptions are propagated."""
    with pytest.raises(RuntimeError) as exc_info:
        runner.run(failing_generator, {}, {"strategy": "all"})
    assert "Generator failed" in str(exc_info.value)


def test_run_unknown_strategy(runner):
    """Test that unknown strategy raises error."""
    with pytest.raises(ValueError) as exc_info:
        runner.run(simple_generator, {}, {"strategy": "unknown"})
    assert "Unknown generator strategy" in str(exc_info.value)


def test_shutdown(runner):
    """Test runner shutdown."""
    runner.run(simple_generator, {}, {"strategy": "last"})
    runner.shutdown(wait=True)
    # Verify shutdown doesn't raise errors