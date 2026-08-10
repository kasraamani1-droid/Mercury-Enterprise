from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone

from ..events.bus import event_bus
from ..events.models import PlatformEvent
from .base import BaseConnector
from .models import ConnectorHealthEvent, ConnectorRecord, ConnectorState, NormalizedObservation
from .providers import MockFlightConnector, MockWeatherConnector
from .registry import registry

registry.register("mock-flight", MockFlightConnector)
registry.register("mock-weather", MockWeatherConnector)

MAX_HEALTH_HISTORY = 200
MAX_RETRIES = 3
BACKOFF_SECONDS = 0.05


class ConnectorManager:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}
        self._lock = asyncio.Lock()
        self._health_history: dict[str, deque[ConnectorHealthEvent]] = defaultdict(
            lambda: deque(maxlen=MAX_HEALTH_HISTORY)
        )
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        records = [
            ConnectorRecord(
                id="flight-demo",
                name="Flight Data Demo",
                provider="mock-flight",
                category="aviation",
                organization_id="org-aviation-east",
                site_id="site-cyul",
            ),
            ConnectorRecord(
                id="weather-demo",
                name="Weather Demo",
                provider="mock-weather",
                category="weather",
                organization_id="org-aviation-east",
                site_id="site-cyul",
            ),
        ]
        for record in records:
            self._connectors[record.id] = registry.create(record)
            self._record_transition(record.id, None, record.state.value, "seeded", actor="system")

    def _record_transition(
        self,
        connector_id: str,
        from_state: str | None,
        to_state: str,
        message: str,
        actor: str | None = None,
    ) -> None:
        event = ConnectorHealthEvent(
            connector_id=connector_id,
            from_state=from_state,
            to_state=to_state,
            message=message,
            actor=actor,
        )
        self._health_history[connector_id].append(event)
        connector = self.get(connector_id)
        if connector is not None:
            connector.record.last_transition_at = event.occurred_at

    def list_records(self) -> list[ConnectorRecord]:
        return [item.record for item in self._connectors.values()]

    def get(self, connector_id: str) -> BaseConnector | None:
        return self._connectors.get(connector_id)

    def health_history(self, connector_id: str, *, limit: int = 50) -> list[ConnectorHealthEvent]:
        clamped = max(1, min(int(limit), MAX_HEALTH_HISTORY))
        history = list(self._health_history.get(connector_id, []))
        return history[-clamped:][::-1]

    async def start_all(self) -> None:
        for connector_id in list(self._connectors):
            await self.start(connector_id)

    async def stop_all(self) -> None:
        for connector_id in list(self._connectors):
            await self.stop(connector_id)

    async def start(self, connector_id: str, *, actor: str | None = None) -> ConnectorRecord:
        connector = self.get(connector_id)
        if connector is None:
            raise KeyError(connector_id)
        async with self._lock:
            previous = connector.record.state.value
            await connector.start()
            self._record_transition(connector_id, previous, connector.record.state.value, "started", actor=actor)
            return connector.record

    async def stop(self, connector_id: str, *, actor: str | None = None) -> ConnectorRecord:
        connector = self.get(connector_id)
        if connector is None:
            raise KeyError(connector_id)
        async with self._lock:
            previous = connector.record.state.value
            await connector.stop()
            self._record_transition(connector_id, previous, connector.record.state.value, "stopped", actor=actor)
            return connector.record

    async def recover(self, connector_id: str, *, actor: str | None = None) -> ConnectorRecord:
        connector = self.get(connector_id)
        if connector is None:
            raise KeyError(connector_id)
        async with self._lock:
            previous = connector.record.state.value
            await connector.recover()
            self._record_transition(connector_id, previous, connector.record.state.value, "recovered", actor=actor)
            return connector.record

    async def poll(self, connector_id: str, *, actor: str | None = None) -> list[NormalizedObservation]:
        connector = self.get(connector_id)
        if connector is None:
            raise KeyError(connector_id)

        if connector.record.state != ConnectorState.online:
            await self.start(connector_id, actor=actor)

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                observations = await connector.poll()
                connector.record.last_poll_at = datetime.now(timezone.utc)
                connector.record.last_error = None
                connector.record.retry_count = 0
                if connector.record.state != ConnectorState.online:
                    previous = connector.record.state.value
                    connector.record.state = ConnectorState.online
                    self._record_transition(
                        connector_id, previous, ConnectorState.online.value, "poll recovered", actor=actor
                    )
                for observation in observations:
                    await event_bus.publish(
                        PlatformEvent(
                            event_type="observation.received",
                            source=connector_id,
                            payload=observation.model_dump(mode="json"),
                        )
                    )
                return observations
            except Exception as exc:
                last_error = exc
                connector.record.retry_count = attempt
                connector.record.last_error = str(exc)
                if attempt < MAX_RETRIES:
                    previous = connector.record.state.value
                    connector.record.state = ConnectorState.degraded
                    self._record_transition(
                        connector_id,
                        previous,
                        ConnectorState.degraded.value,
                        f"poll retry {attempt}: {exc}",
                        actor=actor,
                    )
                    await asyncio.sleep(BACKOFF_SECONDS * attempt)
                else:
                    previous = connector.record.state.value
                    connector.record.state = ConnectorState.error
                    self._record_transition(
                        connector_id,
                        previous,
                        ConnectorState.error.value,
                        f"poll failed: {exc}",
                        actor=actor,
                    )
        assert last_error is not None
        raise last_error


connector_manager = ConnectorManager()
