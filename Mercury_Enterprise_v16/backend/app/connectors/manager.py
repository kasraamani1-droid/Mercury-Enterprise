from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..events.bus import event_bus
from ..events.models import PlatformEvent
from .base import BaseConnector
from .models import ConnectorRecord, ConnectorState, NormalizedObservation
from .providers import MockFlightConnector, MockWeatherConnector
from .registry import registry

registry.register("mock-flight", MockFlightConnector)
registry.register("mock-weather", MockWeatherConnector)


class ConnectorManager:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}
        self._lock = asyncio.Lock()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        records = [
            ConnectorRecord(id="flight-demo", name="Flight Data Demo", provider="mock-flight", category="aviation"),
            ConnectorRecord(id="weather-demo", name="Weather Demo", provider="mock-weather", category="weather"),
        ]
        for record in records:
            self._connectors[record.id] = registry.create(record)

    def list_records(self) -> list[ConnectorRecord]:
        return [item.record for item in self._connectors.values()]

    def get(self, connector_id: str) -> BaseConnector | None:
        return self._connectors.get(connector_id)

    async def start_all(self) -> None:
        async with self._lock:
            await asyncio.gather(*(connector.start() for connector in self._connectors.values()))

    async def stop_all(self) -> None:
        async with self._lock:
            await asyncio.gather(*(connector.stop() for connector in self._connectors.values()))

    async def poll(self, connector_id: str) -> list[NormalizedObservation]:
        connector = self.get(connector_id)
        if connector is None:
            raise KeyError(connector_id)
        if connector.record.state != ConnectorState.online:
            await connector.start()
        try:
            observations = await connector.poll()
            connector.record.last_poll_at = datetime.now(timezone.utc)
            connector.record.last_error = None
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
            connector.record.state = ConnectorState.error
            connector.record.last_error = str(exc)
            raise


connector_manager = ConnectorManager()
