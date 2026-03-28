"""Event bus implementation for pub/sub communication."""

import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List


@dataclass
class Event:
    """Event data structure."""

    type: str
    payload: Dict[str, Any]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


class EventBus:
    """Simple event bus for synchronous event dispatch."""

    _subscribers: Dict[str, List[Callable[[Event], None]]] = {}
    _history: List[Event] = []

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable[[Event], None]):
        """Subscribe to an event type."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def publish(cls, event_type: str, payload: Dict[str, Any] = None):
        """Publish an event to all subscribers."""
        if payload is None:
            payload = {}

        event = Event(type=event_type, payload=payload)
        cls._history.append(event)

        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error handling event {event_type}: {e}")

        # Wildcard subscribers (for logging/debugging)
        if "*" in cls._subscribers:
            for callback in cls._subscribers["*"]:
                try:
                    callback(event)
                except Exception:
                    pass

    @classmethod
    def get_history(cls) -> List[Event]:
        """Get event history."""
        return cls._history.copy()

    @classmethod
    def clear_history(cls):
        """Clear event history."""
        cls._history.clear()

    @classmethod
    def reset(cls):
        """Reset all subscribers and history. Useful for testing."""
        cls._subscribers.clear()
        cls._history.clear()
