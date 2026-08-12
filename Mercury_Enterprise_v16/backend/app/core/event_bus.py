from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Awaitable, Callable
from uuid import uuid4

from .events import EventType

logger = logging.getLogger("mercury.event_bus")

EventCallback = Callable[["Event"], Any | Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class Event:
    event_type: str
    payload: dict[str, Any]
    source: str = "mercury"
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": self.payload,
        }


class EventBus:
    def __init__(self, history_limit: int = 1_000) -> None:
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._history: list[Event] = []
        self._history_limit = history_limit
        self._lock = RLock()

    def subscribe(
        self,
        event_type: EventType | str,
        callback: EventCallback,
    ) -> None:
        event_name = str(event_type)

        with self._lock:
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

        logger.info(
            "Subscriber registered event_type=%s callback=%s",
            event_name,
            getattr(callback, "__name__", repr(callback)),
        )

    def unsubscribe(
        self,
        event_type: EventType | str,
        callback: EventCallback,
    ) -> bool:
        event_name = str(event_type)

        with self._lock:
            callbacks = self._subscribers.get(event_name, [])

            if callback not in callbacks:
                return False

            callbacks.remove(callback)

            if not callbacks:
                self._subscribers.pop(event_name, None)

        return True

    async def publish(
        self,
        event_type: EventType | str,
        payload: dict[str, Any],
        source: str = "mercury",
    ) -> Event:
        event = Event(
            event_type=str(event_type),
            payload=payload,
            source=source,
        )

        with self._lock:
            self._history.append(event)

            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit :]

            callbacks = list(self._subscribers.get(event.event_type, []))
            wildcard_callbacks = list(self._subscribers.get("*", []))

        logger.info(
            "Event published event_id=%s event_type=%s source=%s payload=%s",
            event.event_id,
            event.event_type,
            event.source,
            event.payload,
        )

        for callback in callbacks + wildcard_callbacks:
            try:
                result = callback(event)

                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception(
                    "Event subscriber failed event_id=%s event_type=%s",
                    event.event_id,
                    event.event_type,
                )

        return event

    def history(
        self,
        event_type: EventType | str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        safe_limit = max(1, min(limit, self._history_limit))

        with self._lock:
            events = list(self._history)

        if event_type is not None:
            event_name = str(event_type)
            events = [
                event
                for event in events
                if event.event_type == event_name
            ]

        return events[-safe_limit:]

    def subscriber_count(
        self,
        event_type: EventType | str | None = None,
    ) -> int:
        with self._lock:
            if event_type is None:
                return sum(
                    len(callbacks)
                    for callbacks in self._subscribers.values()
                )

            return len(self._subscribers.get(str(event_type), []))


event_bus = EventBus()