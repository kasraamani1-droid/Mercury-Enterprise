from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from ..core.event_bus import Event, EventBus, event_bus
from .timeline_models import TimelineEntry

logger = logging.getLogger("mercury.timeline")


class TimelineManager:
    """Manages mission timeline entries and subscribes to the shared event bus."""

    def __init__(
        self,
        event_bus_instance: EventBus | None = None,
        max_history: int = 250,
    ) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._max_history = max(1, max_history)
        self._entries: list[TimelineEntry] = []
        self._lock = RLock()
        self._subscribed = False
        self._subscribe()

    @property
    def max_history(self) -> int:
        return self._max_history

    def _subscribe(self) -> None:
        if self._subscribed:
            return

        self._event_bus.subscribe("*", self._handle_bus_event)
        self._subscribed = True
        logger.info("Timeline manager subscribed to event bus")

    def _handle_bus_event(self, event: Event) -> None:
        self.add_event(
            event_type=event.event_type,
            severity="info",
            source=event.source,
            message=self._build_message(event.event_type, event.payload),
            metadata=event.payload,
            timestamp=event.occurred_at,
        )

    def _build_message(self, event_type: str, payload: dict[str, Any] | None) -> str:
        if payload and isinstance(payload.get("message"), str):
            return payload["message"]

        parts = event_type.split(".")
        if not parts:
            return "Event recorded"

        if len(parts) == 1:
            return parts[0].replace("_", " ").capitalize()

        return f"{parts[0].replace('_', ' ').capitalize()} {parts[-1].replace('_', ' ').lower()}"

    def _normalize_timestamp(self, timestamp: datetime | None) -> datetime:
        if timestamp is None:
            return datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    def add_event(
        self,
        event_type: str,
        severity: str = "info",
        source: str = "mercury",
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> TimelineEntry:
        """Add a new timeline entry and enforce the configured history limit."""

        with self._lock:
            entry = TimelineEntry(
                event_type=str(event_type),
                severity=severity,
                source=source,
                message=message or self._build_message(str(event_type), metadata),
                metadata=metadata or {},
                timestamp=self._normalize_timestamp(timestamp),
            )
            self._entries.append(entry)
            if len(self._entries) > self._max_history:
                self._entries = self._entries[-self._max_history :]

            logger.debug(
                "Timeline entry recorded event_type=%s source=%s severity=%s",
                entry.event_type,
                entry.source,
                entry.severity,
            )
            return entry

    def get_events(
        self,
        event_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        limit: int | None = None,
        sort_desc: bool = False,
    ) -> list[TimelineEntry]:
        """Return timeline entries filtered and sorted according to the supplied criteria."""

        with self._lock:
            entries = list(self._entries)

        if event_type is not None:
            entries = [entry for entry in entries if entry.event_type == event_type]
        if severity is not None:
            entries = [entry for entry in entries if entry.severity == severity]
        if source is not None:
            entries = [entry for entry in entries if entry.source == source]

        entries.sort(key=lambda entry: entry.timestamp)
        if sort_desc:
            entries.reverse()

        if limit is not None:
            return entries[: max(0, limit)]
        return entries

    def clear(self) -> None:
        """Remove all timeline entries."""

        with self._lock:
            self._entries.clear()

    def last(self) -> TimelineEntry | None:
        """Return the most recently added entry, if one exists."""

        with self._lock:
            if not self._entries:
                return None
            return self._entries[-1]

    def export_json(self, sort_desc: bool = True) -> list[dict[str, Any]]:
        """Export the timeline as a JSON-serializable list of dictionaries."""

        return [entry.to_dict() for entry in self.get_events(sort_desc=sort_desc)]
