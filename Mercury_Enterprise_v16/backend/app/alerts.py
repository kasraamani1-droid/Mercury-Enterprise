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
    organization_id: str | None = None
    site_id: str | None = None

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
            "organization_id": self.organization_id,
            "site_id": self.site_id,
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
        payload = event.payload if isinstance(event.payload, dict) else {}
        org_id = payload.get("organization_id")
        site_id = payload.get("site_id")
        self.create_alert(
            incident_id=payload.get("incident_id"),
            severity="info",
            title=self._default_title(event.event_type),
            message=payload.get("message") if isinstance(payload, dict) else "Event received",
            source=event.source,
            metadata=payload,
            organization_id=str(org_id) if org_id else None,
            site_id=str(site_id) if site_id else None,
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
        organization_id: str | None = None,
        site_id: str | None = None,
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
                organization_id=str(organization_id) if organization_id else None,
                site_id=str(site_id) if site_id else None,
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
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> list[AlertEntry]:
        """Return alerts filtered by tenant, incident, acknowledgement, and optional limit.

        Tenant rules:
        - When organization_id is set, return tenant-owned alerts for that org
          (and site when site_id is set), plus platform/system alerts with no org.
        - When organization_id is omitted, return all alerts (internal/advisory use).
        """
        with self._lock:
            alerts = list(self._alerts)

        if organization_id is not None:
            org = str(organization_id)
            site = str(site_id) if site_id is not None else None

            def _visible(alert: AlertEntry) -> bool:
                if not alert.organization_id:
                    return True  # platform/system alert
                if alert.organization_id != org:
                    return False
                if site is not None and alert.site_id and alert.site_id != site:
                    return False
                return True

            alerts = [alert for alert in alerts if _visible(alert)]

        if incident_id is not None:
            alerts = [alert for alert in alerts if alert.incident_id == incident_id]
        if acknowledged is not None:
            alerts = [alert for alert in alerts if alert.acknowledged is acknowledged]

        alerts.sort(key=lambda item: item.created_at, reverse=True)
        if limit is not None:
            return alerts[: max(0, limit)]
        return alerts

    def get_alert(
        self,
        alert_id: str,
        *,
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> AlertEntry | None:
        """Fetch one alert if visible to the given tenant scope."""
        with self._lock:
            for alert in self._alerts:
                if alert.id != alert_id:
                    continue
                if organization_id is not None:
                    org = str(organization_id)
                    if alert.organization_id and alert.organization_id != org:
                        return None
                    if (
                        site_id is not None
                        and alert.site_id
                        and alert.organization_id
                        and alert.site_id != str(site_id)
                    ):
                        return None
                return alert
        return None

    def acknowledge(
        self,
        alert_id: str,
        *,
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> AlertEntry | None:
        """Acknowledge an alert by identifier when visible to the tenant."""
        alert = self.get_alert(alert_id, organization_id=organization_id, site_id=site_id)
        if alert is None:
            return None
        with self._lock:
            alert.acknowledged = True
            return alert

    def clear(self) -> None:
        """Remove all alerts."""
        with self._lock:
            self._alerts.clear()

    def export_json(
        self,
        *,
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Export alerts as JSON-serializable dictionaries."""
        return [
            alert.to_dict()
            for alert in self.get_alerts(organization_id=organization_id, site_id=site_id)
        ]
