from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from .core.event_bus import Event, EventBus, event_bus

logger = logging.getLogger("mercury.alerts")


@dataclass(slots=True)
class AlertEntry:
    """Represents a backend-generated alert for an incident or mission event."""

    id: str = field(default_factory=lambda: str(uuid4()))
    incident_id: str | None = None
    severity: str = "info"
    title: str = ""
    message: str = ""
    source: str = "mercury"
    acknowledged: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "acknowledged": self.acknowledged,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class AlertManager:
    """Stores and distributes backend alerts derived from incidents and event bus activity."""

    def __init__(
        self,
        event_bus_instance: EventBus | None = None,
        max_history: int = 250,
    ) -> None:
        self._event_bus = event_bus_instance or event_bus
        self._max_history = max(1, max_history)
        self._alerts: list[AlertEntry] = []
        self._lock = RLock()
        self._subscribed = False
        self._subscribe()

    def _subscribe(self) -> None:
        if self._subscribed:
            return
        self._event_bus.subscribe("*", self._handle_bus_event)
        self._subscribed = True
        logger.info("Alert manager subscribed to event bus")

    def _handle_bus_event(self, event: Event) -> None:
        self.create_alert(
            incident_id=None,
            severity="info",
            title=self._default_title(event.event_type),
            message=event.payload.get("message") if isinstance(event.payload, dict) else "Event received",
            source=event.source,
            metadata=event.payload,
        )

    def _default_title(self, event_type: str) -> str:
        if event_type == "ai.alert":
            return "AI alert"
        if event_type.endswith(".completed"):
            return "Mission completed"
        if event_type.endswith(".started"):
            return "Mission started"
        return event_type.replace(".", " ").title()

    def create_alert(
        self,
        incident_id: str | None,
        severity: str,
        title: str,
        message: str,
        source: str = "mercury",
        metadata: dict[str, Any] | None = None,
    ) -> AlertEntry:
        """Create a new alert and enforce the configured history limit."""
        with self._lock:
            alert = AlertEntry(
                incident_id=incident_id,
                severity=severity,
                title=title,
                message=message,
                source=source,
                metadata=metadata or {},
            )
            self._alerts.append(alert)
            if len(self._alerts) > self._max_history:
                self._alerts = self._alerts[-self._max_history :]
            logger.debug("Alert recorded title=%s severity=%s", alert.title, alert.severity)
            return alert

    def get_alerts(
        self,
        incident_id: str | None = None,
        limit: int | None = None,
        acknowledged: bool | None = None,
    ) -> list[AlertEntry]:
        """Return alerts filtered by incident, acknowledgement state, and optional limit."""
        with self._lock:
            alerts = list(self._alerts)

        if incident_id is not None:
            alerts = [alert for alert in alerts if alert.incident_id == incident_id]
        if acknowledged is not None:
            alerts = [alert for alert in alerts if alert.acknowledged is acknowledged]

        alerts.sort(key=lambda item: item.created_at, reverse=True)
        if limit is not None:
            return alerts[: max(0, limit)]
        return alerts

    def acknowledge(self, alert_id: str) -> AlertEntry | None:
        """Acknowledge an alert by identifier."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    return alert
        return None

    def clear(self) -> None:
        """Remove all alerts."""
        with self._lock:
            self._alerts.clear()

    def export_json(self) -> list[dict[str, Any]]:
        """Export alerts as JSON-serializable dictionaries."""
        return [alert.to_dict() for alert in self.get_alerts()]
