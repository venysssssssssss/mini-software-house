"""WebSocket streaming with EventBus bridge."""

import asyncio
from typing import Dict, List

from ..core.events import Event


class EventStreamManager:
    """Bridges sync EventBus to async WebSocket clients."""

    def __init__(self):
        self._queues: Dict[int, List[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self, run_id: int) -> asyncio.Queue:
        """Subscribe to events for a pipeline run."""
        queue: asyncio.Queue = asyncio.Queue()
        if run_id not in self._queues:
            self._queues[run_id] = []
        self._queues[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: int, queue: asyncio.Queue):
        """Remove a subscriber."""
        if run_id in self._queues:
            self._queues[run_id] = [q for q in self._queues[run_id] if q is not queue]
            if not self._queues[run_id]:
                del self._queues[run_id]

    def push_event(self, event: Event):
        """Push event to all subscribers. Called from sync EventBus callback."""
        for run_id, queues in self._queues.items():
            for queue in queues:
                try:
                    queue.put_nowait({"type": event.type, "payload": event.payload})
                except asyncio.QueueFull:
                    pass

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Store the event loop for thread-safe puts."""
        self._loop = loop


event_stream_manager = EventStreamManager()
