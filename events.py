from typing import Callable, Dict, List, Any
from dataclasses import dataclass
import datetime

@dataclass
class Event:
    type: str
    payload: Dict[str, Any]
    timestamp: datetime.datetime = datetime.datetime.now()

class EventBus:
    _subscribers: Dict[str, List[Callable[[Event], None]]] = {}
    _history: List[Event] = []

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable[[Event], None]):
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def publish(cls, event_type: str, payload: Dict[str, Any] = None):
        if payload is None:
            payload = {}
        
        event = Event(type=event_type, payload=payload)
        cls._history.append(event)
        
        # Simple synchronous dispatch for MVP
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