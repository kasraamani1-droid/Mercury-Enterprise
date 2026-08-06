from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable

from .models import PlatformEvent

EventHandler = Callable[[PlatformEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[PlatformEvent] = []
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event: PlatformEvent) -> None:
        async with self._lock:
            self._history.append(event)
            self._history = self._history[-500:]
        handlers = [*self._subscribers.get(event.event_type, []), *self._subscribers.get("*", [])]
        if handlers:
            await asyncio.gather(*(handler(event) for handler in handlers), return_exceptions=True)

    def recent(self, limit: int = 50) -> list[PlatformEvent]:
        bounded = max(1, min(limit, 500))
        return list(reversed(self._history[-bounded:]))


event_bus = EventBus()
