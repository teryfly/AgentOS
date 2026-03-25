"""
Mock event bus for testing.

Records published events for verification.
"""
from typing import Any, Callable, Awaitable


class MockEventBus:
    """
    Mock EventBus that records all published events.
    """
    
    def __init__(self):
        self.published_events: list[Any] = []
        self.subscribers: dict[type, list[Callable]] = {}
    
    async def publish(self, event: Any) -> None:
        """Record published event."""
        self.published_events.append(event)
        
        # Call subscribers
        event_type = type(event)
        handlers = self.subscribers.get(event_type, [])
        for handler in handlers:
            await handler(event)
    
    def subscribe(self, event_type: type, handler: Callable[[Any], Awaitable[None]]) -> None:
        """Register event handler."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def get_events_by_type(self, event_type: type) -> list[Any]:
        """Get all published events of specific type."""
        return [e for e in self.published_events if isinstance(e, event_type)]
    
    def clear(self) -> None:
        """Clear recorded events."""
        self.published_events.clear()