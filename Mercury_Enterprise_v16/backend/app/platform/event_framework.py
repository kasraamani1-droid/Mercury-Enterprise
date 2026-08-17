"""Event Framework — canonical in-process event bus for AEOS (future bus-ready)."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ..core.event_bus import Event, event_bus as core_bus

logger = logging.getLogger("mercury.event_framework")

EventHandler = Callable[["PlatformEvent"], Awaitable[None] | None]


class PlatformEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    source: str = "mercury"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
    organization_id: str = ""
    correlation_id: str = ""
    # Program 17 observability (optional / additive)
    trace_id: str = ""
    actor: str = ""
    target_service: str = ""
    severity: str = "info"
    status: str = "published"
    duration_ms: int = 0
    event_version: str = "1.0"


class EventFramework:
    """Unified publish/subscribe.

    - Mirrors to core.event_bus for mission/ops/decision subscribers
    - Keeps AEOS typed PlatformEvent history for connectors/integrations
    - Future: swap backend for Redis/NATS without changing publishers
    """

    def __init__(self, history_limit: int = 1_000) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[PlatformEvent] = []
        self._history_limit = history_limit
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    async def publish(self, event: PlatformEvent | None = None, **kwargs: Any) -> PlatformEvent:
        if event is None:
            event = PlatformEvent(**kwargs)
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit :]

        # Mirror into core bus (async)
        try:
            await core_bus.publish(
                event.event_type,
                {
                    **event.payload,
                    "organization_id": event.organization_id,
                    "correlation_id": event.correlation_id,
                    "platform_event_id": event.event_id,
                },
                source=event.source,
            )
        except Exception:
            logger.exception("core event bus mirror failed event_type=%s", event.event_type)

        handlers = [
            *self._subscribers.get(event.event_type, []),
            *self._subscribers.get("*", []),
        ]
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
                    await result  # type: ignore[misc]
            except Exception:
                logger.exception("event handler failed event_type=%s", event.event_type)
        return event

    def publish_sync(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        source: str = "mercury",
        organization_id: str = "",
        correlation_id: str = "",
        trace_id: str = "",
        actor: str = "",
        target_service: str = "",
        severity: str = "info",
        duration_ms: int = 0,
        event_version: str = "1.0",
        dual_write: bool = True,
    ) -> PlatformEvent:
        """Sync helper for service-layer emits (schedules async when loop running).

        When ``dual_write`` is True (default), mapped bus types are best-effort
        mirrored into Enterprise Event Fabric. Fabric→Framework mirrors must pass
        ``dual_write=False`` to avoid recursion.
        """
        corr = correlation_id or str(uuid4())
        merged_payload = {
            **payload,
            "actor": actor or payload.get("actor") or "",
            "correlation_id": corr,
        }
        event = PlatformEvent(
            event_type=event_type,
            payload=payload,
            source=source,
            organization_id=organization_id,
            correlation_id=corr,
            trace_id=trace_id or corr,
            actor=actor,
            target_service=target_service,
            severity=severity,
            duration_ms=duration_ms,
            event_version=event_version,
        )
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event))
        except RuntimeError:
            # No running loop — mirror sync into core history via subscribe-less append path
            core_event = Event(event_type=event_type, payload=payload, source=source)
            with core_bus._lock:  # noqa: SLF001 — intentional bridge
                core_bus._history.append(core_event)
                if len(core_bus._history) > core_bus._history_limit:
                    core_bus._history = core_bus._history[-core_bus._history_limit :]
        if dual_write and organization_id:
            try:
                from ..event_fabric.dual_write import maybe_dual_write_to_fabric

                maybe_dual_write_to_fabric(
                    bus_event_type=event_type,
                    payload=merged_payload,
                    organization_id=organization_id,
                    source=source,
                )
            except Exception:
                logger.exception("dual-write hook failed event_type=%s", event_type)
        return event

    def recent(self, limit: int = 50) -> list[PlatformEvent]:
        bounded = max(1, min(limit, self._history_limit))
        return list(reversed(self._history[-bounded:]))

    def history(self, event_type: str | None = None, limit: int = 100) -> list[PlatformEvent]:
        safe = max(1, min(limit, self._history_limit))
        events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-safe:]


event_framework = EventFramework()
