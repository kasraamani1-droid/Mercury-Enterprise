from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter

from .models import ConnectorHealth, ConnectorRecord, ConnectorState, NormalizedObservation


class BaseConnector(ABC):
    def __init__(self, record: ConnectorRecord) -> None:
        self.record = record

    async def start(self) -> None:
        self.record.state = ConnectorState.online

    async def stop(self) -> None:
        self.record.state = ConnectorState.offline

    @abstractmethod
    async def poll(self) -> list[NormalizedObservation]:
        raise NotImplementedError

    async def health(self) -> ConnectorHealth:
        started = perf_counter()
        message = "ok" if self.record.state == ConnectorState.online else "connector not online"
        return ConnectorHealth(
            connector_id=self.record.id,
            state=self.record.state,
            latency_ms=round((perf_counter() - started) * 1000, 2),
            message=message,
        )
